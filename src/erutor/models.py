"""Data models for Erutor representing media metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Rating:
    name: str  # e.g. "imdb", "themoviedb", "tomatometerallcritics", "default"
    value: float
    votes: int = 0
    max_value: int = 10
    is_default: bool = False


@dataclass
class Person:
    name: str
    role: Optional[str] = None
    person_type: str = "Actor"  # "Actor", "Director", "Writer", "Producer"
    thumb: Optional[str] = None
    profile: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None


@dataclass
class VideoStreamDetails:
    codec: Optional[str] = None
    aspect: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[int] = None
    bitrate: Optional[int] = None
    framerate: Optional[float] = None


@dataclass
class AudioStreamDetails:
    codec: Optional[str] = None
    language: Optional[str] = None
    channels: Optional[int] = None
    bitrate: Optional[int] = None
    sampling_rate: Optional[int] = None


@dataclass
class SubtitleStreamDetails:
    language: Optional[str] = None


@dataclass
class FileInfo:
    video: Optional[VideoStreamDetails] = None
    audio: list[AudioStreamDetails] = field(default_factory=list)
    subtitles: list[SubtitleStreamDetails] = field(default_factory=list)


@dataclass
class MovieMetadata:
    title: str
    original_title: Optional[str] = None
    sort_title: Optional[str] = None
    year: Optional[int] = None
    premiered: Optional[str] = None  # YYYY-MM-DD
    plot: Optional[str] = None
    outline: Optional[str] = None
    tagline: Optional[str] = None
    runtime: Optional[int] = None  # in minutes
    ratings: list[Rating] = field(default_factory=list)
    user_rating: Optional[float] = None
    top250: Optional[int] = None
    genres: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    mpaa: Optional[str] = None
    certification: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    official_website: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    actors: list[Person] = field(default_factory=list)
    directors: list[Person] = field(default_factory=list)
    writers: list[Person] = field(default_factory=list)
    producers: list[Person] = field(default_factory=list)
    posters: list[str] = field(default_factory=list)
    fanarts: list[str] = field(default_factory=list)
    trailer: Optional[str] = None
    languages: list[str] = field(default_factory=list)
    date_added: Optional[str] = None
    file_info: Optional[FileInfo] = None
    source: Optional[str] = None
    edition: Optional[str] = None
    original_filename: Optional[str] = None


@dataclass
class EpisodeMetadata:
    title: str
    season_number: int
    episode_number: int
    original_title: Optional[str] = None
    show_title: Optional[str] = None
    plot: Optional[str] = None
    outline: Optional[str] = None
    aired: Optional[str] = None  # YYYY-MM-DD
    year: Optional[int] = None
    runtime: Optional[int] = None
    ratings: list[Rating] = field(default_factory=list)
    mpaa: Optional[str] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    genres: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    actors: list[Person] = field(default_factory=list)
    directors: list[Person] = field(default_factory=list)
    writers: list[Person] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    date_added: Optional[str] = None
    file_info: Optional[FileInfo] = None
    original_filename: Optional[str] = None
    source: Optional[str] = None


@dataclass
class SeasonMetadata:
    season_number: int
    title: Optional[str] = None
    plot: Optional[str] = None
    outline: Optional[str] = None
    year: Optional[int] = None
    premiered: Optional[str] = None
    release_date: Optional[str] = None
    posters: list[str] = field(default_factory=list)
    date_added: Optional[str] = None


@dataclass
class TVShowMetadata:
    title: str
    original_title: Optional[str] = None
    plot: Optional[str] = None
    outline: Optional[str] = None
    year: Optional[int] = None
    premiered: Optional[str] = None
    status: Optional[str] = None  # e.g. "Ended", "Continuing"
    runtime: Optional[int] = None
    ratings: list[Rating] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    studios: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    mpaa: Optional[str] = None
    certification: Optional[str] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    official_website: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    actors: list[Person] = field(default_factory=list)
    posters: list[str] = field(default_factory=list)
    fanarts: list[str] = field(default_factory=list)
    banners: list[str] = field(default_factory=list)
    named_seasons: dict[int, str] = field(default_factory=dict)
    season_posters: dict[int, list[str]] = field(default_factory=dict)
    season_banners: dict[int, list[str]] = field(default_factory=dict)
    season_thumbs: dict[int, list[str]] = field(default_factory=dict)
    date_added: Optional[str] = None
    seasons: list[SeasonMetadata] = field(default_factory=list)
    episodes: list[EpisodeMetadata] = field(default_factory=list)


@dataclass
class SearchResult:
    id: str  # Provider ID (e.g. IMDb tt..., TVMaze show ID, etc.)
    title: str
    year: Optional[int] = None
    media_type: str = "movie"  # "movie" or "tv"
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    source: str = "imdb"
