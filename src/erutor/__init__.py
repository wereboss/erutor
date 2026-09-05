"""Erutor: A lightweight movie & TV show metadata fetcher and NFO generator."""

from erutor.network import enable_resilient_dns

__version__ = "0.1.1"

# Enable automatic DNS-over-HTTPS fallback if local system DNS fails
enable_resilient_dns()

