"""Artwork and media asset downloader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import certifi
import httpx


def download_image(url: str, target_path: Path, force: bool = False, timeout: float = 20.0) -> bool:
    """Download an image from url to target_path safely using a temporary file."""
    if target_path.exists() and not force:
        return True

    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".tmp")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        with httpx.stream("GET", url, timeout=timeout, headers=headers, verify=certifi.where(), follow_redirects=True) as resp:
            if resp.status_code != 200:
                return False
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=16384):
                    f.write(chunk)

        temp_path.replace(target_path)
        return True
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return False
