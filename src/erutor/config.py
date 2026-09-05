"""Configuration management for Erutor."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclass
class Config:
    tmdb_api_key: Optional[str] = None
    omdb_api_key: Optional[str] = None
    tvdb_api_key: Optional[str] = None
    movie_nfo_name: str = "movie.nfo"
    poster_name: str = "poster.jpg"
    fanart_name: str = "fanart.jpg"
    tvshow_nfo_name: str = "tvshow.nfo"
    season_nfo_name: str = "season.nfo"
    download_images: bool = True

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> Config:
        """Load configuration from config.toml and environment variables."""
        if config_path is None:
            config_dir = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "erutor"
            config_path = config_dir / "config.toml"

        data: dict = {}
        if config_path.is_file():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
            except Exception:
                pass

        providers = data.get("providers", {})
        output = data.get("output", {})

        return cls(
            tmdb_api_key=os.getenv("ERUTOR_TMDB_API_KEY") or providers.get("tmdb_api_key") or None,
            omdb_api_key=os.getenv("ERUTOR_OMDB_API_KEY") or providers.get("omdb_api_key") or None,
            tvdb_api_key=os.getenv("ERUTOR_TVDB_API_KEY") or providers.get("tvdb_api_key") or None,
            movie_nfo_name=output.get("movie_nfo_name", "movie.nfo"),
            poster_name=output.get("poster_name", "poster.jpg"),
            fanart_name=output.get("fanart_name", "fanart.jpg"),
            tvshow_nfo_name=output.get("tvshow_nfo_name", "tvshow.nfo"),
            season_nfo_name=output.get("season_nfo_name", "season.nfo"),
            download_images=output.get("download_images", True),
        )
