"""Base classes and interfaces for metadata fetchers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from erutor.models import MovieMetadata, SearchResult, TVShowMetadata
import certifi
import httpx


def get_http_client(
    timeout: float = 15.0,
    headers: Optional[dict[str, str]] = None,
    follow_redirects: bool = True,
) -> httpx.Client:
    """Create a standardized HTTP client with certifi SSL verification and browser UA."""
    default_headers = {
        "User-Agent": (
            "Erutor/0.1.1 (https://github.com/wereboss/erutor; media-metadata-tool)"
        ),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        default_headers.update(headers)

    ca_bundle = certifi.where()
    try:
        return httpx.Client(
            timeout=timeout,
            headers=default_headers,
            verify=ca_bundle,
            follow_redirects=follow_redirects,
        )
    except Exception:
        return httpx.Client(
            timeout=timeout,
            headers=default_headers,
            follow_redirects=follow_redirects,
        )



class BaseFetcher(ABC):
    """Abstract base class for all metadata providers."""

    name: str = "base"

    @abstractmethod
    def search_movie(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        """Search for movies matching query and optional year."""
        pass

    @abstractmethod
    def get_movie(self, id: str) -> Optional[MovieMetadata]:
        """Fetch detailed metadata for a movie by ID."""
        pass

    @abstractmethod
    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        """Search for TV shows matching query and optional year."""
        pass

    @abstractmethod
    def get_tvshow(self, id: str) -> Optional[TVShowMetadata]:
        """Fetch detailed metadata for a TV show (including seasons and episodes) by ID."""
        pass
