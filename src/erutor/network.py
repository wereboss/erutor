"""Network diagnostics and resilient DNS-over-HTTPS fallback."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import ssl
import urllib.request
from typing import Optional

import certifi
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

orig_getaddrinfo = socket.getaddrinfo
_dns_cache: dict[str, str] = {}
_is_patched = False


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def resolve_doh(host: str) -> Optional[str]:
    """Resolve a hostname to IPv4 using direct IP-based DNS-over-HTTPS (Cloudflare / Google)."""
    if _is_ip(host):
        return host
    if host in _dns_cache:
        return _dns_cache[host]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    endpoints = [
        ("1.1.1.1", "https://1.1.1.1/dns-query?name={}&type=A"),
        ("8.8.8.8", "https://8.8.8.8/resolve?name={}&type=A"),
    ]

    for ip_addr, url in endpoints:
        try:
            req = urllib.request.Request(
                url.format(host),
                headers={"Accept": "application/dns-json", "User-Agent": "Erutor/0.1"},
            )
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for ans in data.get("Answer", []):
                    if ans.get("type") == 1:  # IPv4 A record
                        ip = ans.get("data")
                        _dns_cache[host] = ip
                        return ip
        except Exception:
            continue
    return None


def _resilient_getaddrinfo(host, port, *args, **kwargs):
    if _is_ip(str(host)):
        return orig_getaddrinfo(host, port, *args, **kwargs)

    try:
        return orig_getaddrinfo(host, port, *args, **kwargs)
    except socket.gaierror as e:
        # When system DNS fails (e.g. macOS [Errno 8]), attempt DoH resolution
        ip = resolve_doh(str(host))
        if ip:
            return orig_getaddrinfo(ip, port, *args, **kwargs)
        raise e


def enable_resilient_dns() -> None:
    """Enable automatic fallback to DNS-over-HTTPS when system DNS resolution fails."""
    global _is_patched
    if not _is_patched:
        socket.getaddrinfo = _resilient_getaddrinfo
        _is_patched = True


def run_diagnostics() -> None:
    """Run full network, DNS, and SSL diagnostics for the current machine."""
    table = Table(title="Erutor Network & System Diagnostics", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold", width=32)
    table.add_column("Status", width=14)
    table.add_column("Details")

    # 1. Hostname & Local Resolution
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        table.add_row("Local Hostname", "[green]✓ OK[/green]", f"{hostname} ({local_ip})")
    except Exception as e:
        table.add_row("Local Hostname", "[yellow]⚠️ Warning[/yellow]", f"{hostname} (Cannot resolve locally: {e})")

    # 2. Direct Internet Ping (IP-based)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request("https://1.1.1.1/", headers={"User-Agent": "Erutor/0.1"})
        with urllib.request.urlopen(req, timeout=3.0, context=ctx) as r:
            table.add_row("Direct IP Connectivity", "[green]✓ Connected[/green]", "Connected directly to 1.1.1.1")
    except Exception as e:
        table.add_row("Direct IP Connectivity", "[red]✗ Failed[/red]", f"Cannot reach 1.1.1.1: {e}")

    # 3. System DNS & DoH checks
    domains = [
        ("api.tvmaze.com", "TVMaze (TV Shows)"),
        ("v3.sg.media-imdb.com", "IMDb Suggest (Movies)"),
        ("en.wikipedia.org", "Wikipedia (Movie Details)"),
        ("api.themoviedb.org", "TMDB API"),
    ]

    for domain, desc in domains:
        # Test system DNS
        sys_ip = None
        try:
            addrinfo = orig_getaddrinfo(domain, 443)
            sys_ip = addrinfo[0][4][0] if addrinfo else None
        except Exception:
            pass

        if sys_ip:
            table.add_row(f"DNS: {desc}", "[green]✓ OK[/green]", f"{domain} -> {sys_ip}")
        else:
            # Test DoH fallback
            doh_ip = resolve_doh(domain)
            if doh_ip:
                table.add_row(f"DNS: {desc}", "[yellow]✓ DoH Fallback[/yellow]", f"System DNS failed, resolved via DoH: {doh_ip}")
            else:
                table.add_row(f"DNS: {desc}", "[red]✗ Failed[/red]", f"Cannot resolve {domain} (Check internet / DNS)")

    # 4. HTTPS & SSL Certifi Verification
    try:
        with httpx.Client(verify=certifi.where(), timeout=5.0) as client:
            resp = client.get("https://api.tvmaze.com/shows/1", follow_redirects=True)
            if resp.status_code == 200:
                table.add_row("HTTPS / SSL CA Bundle", "[green]✓ Verified[/green]", f"Certifi bundle: {certifi.where()}")
            else:
                table.add_row("HTTPS / SSL CA Bundle", "[yellow]⚠️ HTTP Error[/yellow]", f"HTTP {resp.status_code}")
    except Exception as e:
        table.add_row("HTTPS / SSL CA Bundle", "[red]✗ SSL Error[/red]", str(e))

    # 5. Proxy Environment
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy or https_proxy:
        table.add_row("HTTP Proxy", "[cyan]Configured[/cyan]", f"HTTP: {http_proxy} | HTTPS: {https_proxy}")
    else:
        table.add_row("HTTP Proxy", "[dim]None[/dim]", "Direct connection")

    console.print(table)
