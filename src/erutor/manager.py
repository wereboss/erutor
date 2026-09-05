"""Erutor manager orchestrating fetchers, NFO generation, and asset downloads."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from erutor.config import Config
from erutor.downloader import download_image
from erutor.fetchers.base import BaseFetcher
from erutor.fetchers.imdb_free import FreeMovieFetcher
from erutor.fetchers.omdb import OMDbFetcher
from erutor.fetchers.tmdb import TMDBFetcher
from erutor.fetchers.tvmaze import TVMazeFetcher
from erutor.models import MovieMetadata, SearchResult, TVShowMetadata
from erutor.nfo import NFOBuilder


def _sanitize_filename(name: str) -> str:
    """Sanitize string for filesystem paths."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    return clean.strip()


class ErutorManager:
    """Core manager handling metadata lookup, NFO building, and asset saving."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()

        # Initialize available movie fetchers
        self.movie_fetchers: list[BaseFetcher] = []
        if self.config.tmdb_api_key:
            self.movie_fetchers.append(TMDBFetcher(self.config.tmdb_api_key))
        if self.config.omdb_api_key:
            self.movie_fetchers.append(OMDbFetcher(self.config.omdb_api_key))
        # Free movie fetcher is always available as default / fallback
        self.movie_fetchers.append(FreeMovieFetcher())

        # Initialize TV fetchers (TVMaze is zero-key, primary)
        self.tv_fetchers: list[BaseFetcher] = [TVMazeFetcher()]
        if self.config.tmdb_api_key:
            self.tv_fetchers.insert(0, TMDBFetcher(self.config.tmdb_api_key))

    def search_movies(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        for fetcher in self.movie_fetchers:
            results = fetcher.search_movie(query, year)
            if results:
                return results
        return []

    def get_movie(self, movie_id: str) -> Optional[MovieMetadata]:
        # Try fetchers in order
        movie = None
        for fetcher in self.movie_fetchers:
            movie = fetcher.get_movie(movie_id)
            if movie:
                break

        if not movie:
            return None

        # If OMDb key is available and movie doesn't have Rotten Tomatoes/Metacritic, enrich it
        if self.config.omdb_api_key and movie.imdb_id:
            omdb = OMDbFetcher(self.config.omdb_api_key)
            omdb_meta = omdb.get_movie(movie.imdb_id)
            if omdb_meta:
                # Merge ratings
                existing_names = {r.name for r in movie.ratings}
                for r in omdb_meta.ratings:
                    if r.name not in existing_names:
                        movie.ratings.append(r)
                if not movie.runtime and omdb_meta.runtime:
                    movie.runtime = omdb_meta.runtime
                if not movie.mpaa and omdb_meta.mpaa:
                    movie.mpaa = omdb_meta.mpaa
                    movie.certification = omdb_meta.mpaa

        return movie

    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        for fetcher in self.tv_fetchers:
            results = fetcher.search_tv(query, year)
            if results:
                return results
        return []

    def get_tvshow(self, show_id: str) -> Optional[TVShowMetadata]:
        for fetcher in self.tv_fetchers:
            show = fetcher.get_tvshow(show_id)
            if show:
                return show
        return None

    def save_movie(
        self,
        movie: MovieMetadata,
        output_dir: Path,
        force: bool = False,
        video_filename: Optional[str] = None,
    ) -> dict[str, Path]:
        """Generate movie.nfo and download poster/fanart."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files: dict[str, Path] = {}

        if video_filename:
            movie.original_filename = video_filename

        # Write movie.nfo
        nfo_path = output_dir / self.config.movie_nfo_name
        nfo_content = NFOBuilder.build_movie_nfo(movie)
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)
        saved_files["nfo"] = nfo_path

        # Download poster
        if self.config.download_images and movie.posters:
            poster_path = output_dir / self.config.poster_name
            if download_image(movie.posters[0], poster_path, force=force):
                saved_files["poster"] = poster_path

        # Download fanart
        if self.config.download_images and movie.fanarts:
            fanart_path = output_dir / self.config.fanart_name
            if download_image(movie.fanarts[0], fanart_path, force=force):
                saved_files["fanart"] = fanart_path

        return saved_files

    def save_tvshow(
        self,
        show: TVShowMetadata,
        output_dir: Path,
        force: bool = False,
    ) -> dict[str, list[Path]]:
        """Generate tvshow.nfo, season.nfo, episode NFOs, and download artwork."""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: dict[str, list[Path]] = {"nfo": [], "images": []}

        # 1. tvshow.nfo
        tvshow_nfo_path = output_dir / self.config.tvshow_nfo_name
        tvshow_nfo_content = NFOBuilder.build_tvshow_nfo(show)
        with open(tvshow_nfo_path, "w", encoding="utf-8") as f:
            f.write(tvshow_nfo_content)
        saved["nfo"].append(tvshow_nfo_path)

        # 2. Show poster & fanart
        if self.config.download_images:
            if show.posters:
                show_poster_path = output_dir / self.config.poster_name
                if download_image(show.posters[0], show_poster_path, force=force):
                    saved["images"].append(show_poster_path)

            if show.fanarts:
                show_fanart_path = output_dir / self.config.fanart_name
                if download_image(show.fanarts[0], show_fanart_path, force=force):
                    saved["images"].append(show_fanart_path)

        # 3. Seasons & Episodes
        episodes_by_season: dict[int, list] = {}
        for ep in show.episodes:
            episodes_by_season.setdefault(ep.season_number, []).append(ep)

        # Process seasons
        for season in show.seasons:
            s_num = season.season_number
            # Season folder naming: "Season 01" or "Season 1"
            season_dir = output_dir / f"Season {s_num}"
            season_dir.mkdir(parents=True, exist_ok=True)

            # season.nfo
            season_nfo_path = season_dir / self.config.season_nfo_name
            season_nfo_content = NFOBuilder.build_season_nfo(season)
            with open(season_nfo_path, "w", encoding="utf-8") as f:
                f.write(season_nfo_content)
            saved["nfo"].append(season_nfo_path)

            # Season poster
            if self.config.download_images and season.posters:
                s_poster_path = season_dir / "poster.jpg"
                if download_image(season.posters[0], s_poster_path, force=force):
                    saved["images"].append(s_poster_path)

            # Episodes for this season
            season_episodes = episodes_by_season.get(s_num, [])
            for ep in season_episodes:
                clean_title = _sanitize_filename(ep.title)
                ep_base_name = f"{_sanitize_filename(show.title)} - S{ep.season_number:02d}E{ep.episode_number:02d} - {clean_title}"

                ep_nfo_path = season_dir / f"{ep_base_name}.nfo"
                ep_nfo_content = NFOBuilder.build_episode_nfo(ep)
                with open(ep_nfo_path, "w", encoding="utf-8") as f:
                    f.write(ep_nfo_content)
                saved["nfo"].append(ep_nfo_path)

                if self.config.download_images and ep.thumbnail_url:
                    ep_thumb_path = season_dir / f"{ep_base_name}-thumb.jpg"
                    if download_image(ep.thumbnail_url, ep_thumb_path, force=force):
                        saved["images"].append(ep_thumb_path)

        return saved
