"""Base classes and interfaces for metadata fetchers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from erutor.models import MovieMetadata, SearchResult, TVShowMetadata


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
