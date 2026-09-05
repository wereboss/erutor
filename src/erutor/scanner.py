"""Local directory scanner for discovering movies and TV shows."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from erutor.parser import TitleParser, VIDEO_EXTENSIONS

# Common subtitle extensions that might accompany videos
SUBTITLE_EXTENSIONS = {".srt", ".sub", ".idx", ".vtt", ".ass", ".ssa"}

# Video files to ignore (samples, trailers)
IGNORE_KEYWORDS = ["sample", "trailer", "preview"]


@dataclass
class ScannedEpisode:
    path: Path
    season_number: int
    episode_number: int
    episode_end: Optional[int] = None
    has_nfo: bool = False
    has_thumb: bool = False


@dataclass
class ScannedItem:
    path: Path  # Root path for this item (movie folder or file, or tv show folder)
    media_type: str  # "movie" or "tv"
    title: str
    year: Optional[int] = None
    video_file: Optional[Path] = None  # Single video file if movie
    has_nfo: bool = False
    has_poster: bool = False
    has_fanart: bool = False
    existing_metadata_desc: str = "None"

    # TV-specific attributes
    seasons: dict[int, list[ScannedEpisode]] = field(default_factory=dict)
    existing_seasons: set[int] = field(default_factory=set)


def _is_sample_or_trailer(path: Path) -> bool:
    stem = path.stem.lower()
    return any(k in stem for k in IGNORE_KEYWORDS)


class DirectoryScanner:
    """Recursively scans a directory for movies and TV series."""

    @classmethod
    def scan(cls, root_dir: Path) -> list[ScannedItem]:
        if not root_dir.exists() or not root_dir.is_dir():
            return []

        # Find all video files
        all_videos: list[Path] = []
        for root, _, files in os.walk(root_dir):
            for f in files:
                f_path = Path(root) / f
                if f_path.suffix.lower() in VIDEO_EXTENSIONS and f_path.suffix.lower() != ".nfo":
                    if not _is_sample_or_trailer(f_path):
                        all_videos.append(f_path)

        if not all_videos:
            return []

        # Step 1: Identify TV episodes vs Movie files
        tv_videos: list[tuple[Path, int, int, Optional[int]]] = []
        movie_candidates: list[Path] = []

        for v in all_videos:
            parsed = TitleParser.parse(v)
            if parsed.media_type == "tv" and parsed.season is not None and parsed.episode is not None:
                tv_videos.append((v, parsed.season, parsed.episode, parsed.episode_end))
            else:
                # Check if parent or grandparent indicates a TV season
                parent_name = v.parent.name.lower()
                parsed_parent = TitleParser.parse(v.parent)
                if (
                    "season" in parent_name
                    or "specials" in parent_name
                    or (parsed_parent.media_type == "tv" and parsed_parent.season is not None)
                ):
                    # Likely a TV episode inside Season folder
                    s_num = parsed_parent.season or 1
                    ep_parsed = TitleParser.parse(v)
                    ep_num = ep_parsed.episode or 1
                    tv_videos.append((v, s_num, ep_num, ep_parsed.episode_end))
                else:
                    movie_candidates.append(v)

        scanned_items: list[ScannedItem] = []

        # Step 2: Group TV episodes by TV show root directory
        tv_groups: dict[Path, list[tuple[Path, int, int, Optional[int]]]] = {}
        for v, s_num, ep_num, ep_end in tv_videos:
            # Determine show root folder
            parent = v.parent
            if "season" in parent.name.lower() or "specials" in parent.name.lower():
                show_root = parent.parent
            else:
                show_root = parent

            tv_groups.setdefault(show_root, []).append((v, s_num, ep_num, ep_end))

        for show_root, ep_list in tv_groups.items():
            parsed_show = TitleParser.parse(show_root)
            title = parsed_show.title or show_root.name
            year = parsed_show.year

            # Check existing metadata
            has_tv_nfo = (show_root / "tvshow.nfo").is_file()
            has_poster = (show_root / "poster.jpg").is_file()
            has_fanart = (show_root / "fanart.jpg").is_file()

            seasons_dict: dict[int, list[ScannedEpisode]] = {}
            existing_seasons: set[int] = set()
            any_ep_nfo = False

            for ep_path, s_num, ep_num, ep_end in ep_list:
                existing_seasons.add(s_num)
                ep_nfo = ep_path.with_suffix(".nfo").is_file()
                ep_thumb = (
                    ep_path.with_name(f"{ep_path.stem}-thumb.jpg").is_file()
                    or ep_path.with_name(f"{ep_path.stem}.thumb.jpg").is_file()
                )
                if ep_nfo:
                    any_ep_nfo = True

                seasons_dict.setdefault(s_num, []).append(
                    ScannedEpisode(
                        path=ep_path,
                        season_number=s_num,
                        episode_number=ep_num,
                        episode_end=ep_end,
                        has_nfo=ep_nfo,
                        has_thumb=ep_thumb,
                    )
                )

            # Metadata status description
            existing_parts = []
            if has_tv_nfo:
                existing_parts.append("tvshow.nfo")
            if has_poster:
                existing_parts.append("poster")
            if any_ep_nfo:
                existing_parts.append("episode NFOs")

            status_desc = ", ".join(existing_parts) if existing_parts else "None"

            scanned_items.append(
                ScannedItem(
                    path=show_root,
                    media_type="tv",
                    title=title,
                    year=year,
                    has_nfo=has_tv_nfo,
                    has_poster=has_poster,
                    has_fanart=has_fanart,
                    existing_metadata_desc=status_desc,
                    seasons=seasons_dict,
                    existing_seasons=existing_seasons,
                )
            )

        # Step 3: Process movie candidates
        # If parent folder contains only this 1 movie file, use the parent folder as the movie directory
        parent_counts: dict[Path, list[Path]] = {}
        for m in movie_candidates:
            parent_counts.setdefault(m.parent, []).append(m)

        for parent_dir, files in parent_counts.items():
            if len(files) == 1 and parent_dir != root_dir:
                # Dedicated movie folder
                m_file = files[0]
                parsed_folder = TitleParser.parse(parent_dir)
                parsed_file = TitleParser.parse(m_file)

                title = parsed_folder.title or parsed_file.title
                year = parsed_folder.year or parsed_file.year

                has_nfo = (parent_dir / "movie.nfo").is_file() or m_file.with_suffix(".nfo").is_file()
                has_poster = (
                    (parent_dir / "poster.jpg").is_file()
                    or (parent_dir / "poster.png").is_file()
                    or m_file.with_name(f"{m_file.stem}-poster.jpg").is_file()
                )
                has_fanart = (parent_dir / "fanart.jpg").is_file() or m_file.with_name(f"{m_file.stem}-fanart.jpg").is_file()

                existing_parts = []
                if has_nfo:
                    existing_parts.append("movie.nfo")
                if has_poster:
                    existing_parts.append("poster")
                if has_fanart:
                    existing_parts.append("fanart")

                status_desc = ", ".join(existing_parts) if existing_parts else "None"

                scanned_items.append(
                    ScannedItem(
                        path=parent_dir,
                        media_type="movie",
                        title=title,
                        year=year,
                        video_file=m_file,
                        has_nfo=has_nfo,
                        has_poster=has_poster,
                        has_fanart=has_fanart,
                        existing_metadata_desc=status_desc,
                    )
                )
            else:
                # Flat folder with multiple standalone movie files
                for m_file in files:
                    parsed_file = TitleParser.parse(m_file)
                    has_nfo = m_file.with_suffix(".nfo").is_file()
                    has_poster = m_file.with_name(f"{m_file.stem}-poster.jpg").is_file()
                    has_fanart = m_file.with_name(f"{m_file.stem}-fanart.jpg").is_file()

                    existing_parts = []
                    if has_nfo:
                        existing_parts.append(".nfo")
                    if has_poster:
                        existing_parts.append("poster")
                    if has_fanart:
                        existing_parts.append("fanart")

                    status_desc = ", ".join(existing_parts) if existing_parts else "None"

                    scanned_items.append(
                        ScannedItem(
                            path=m_file.parent,
                            media_type="movie",
                            title=parsed_file.title,
                            year=parsed_file.year,
                            video_file=m_file,
                            has_nfo=has_nfo,
                            has_poster=has_poster,
                            has_fanart=has_fanart,
                            existing_metadata_desc=status_desc,
                        )
                    )

        return scanned_items
