"""TMDB (The Movie Database) API fetcher for rich movie & TV metadata and high-resolution artwork."""

from __future__ import annotations

from typing import Optional

import httpx

from erutor.fetchers.base import BaseFetcher
from erutor.models import (
    EpisodeMetadata,
    MovieMetadata,
    Person,
    Rating,
    SearchResult,
    SeasonMetadata,
    TVShowMetadata,
)


class TMDBFetcher(BaseFetcher):
    """Fetcher for movies and TV shows using TMDB API v3."""

    name = "tmdb"
    BASE_URL = "https://api.themoviedb.org/3"
    IMG_BASE_URL = "https://image.tmdb.org/t/p/original"

    def __init__(self, api_key: str, client: Optional[httpx.Client] = None):
        self.api_key = api_key
        self.client = client or httpx.Client(
            headers={"User-Agent": "Erutor/0.1 (https://github.com/erutor)"},
            timeout=15.0,
        )

    def search_movie(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        params = {"api_key": self.api_key, "query": query}
        if year:
            params["year"] = str(year)

        try:
            resp = self.client.get(f"{self.BASE_URL}/search/movie", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            return []

        search_results: list[SearchResult] = []
        for r in results:
            r_id = str(r.get("id"))
            title = r.get("title")
            release_date = r.get("release_date")
            r_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None
            overview = r.get("overview")
            poster_path = r.get("poster_path")
            poster_url = f"{self.IMG_BASE_URL}{poster_path}" if poster_path else None

            search_results.append(
                SearchResult(
                    id=r_id,
                    title=title,
                    year=r_year,
                    media_type="movie",
                    overview=overview,
                    poster_url=poster_url,
                    source=self.name,
                )
            )
        return search_results

    def get_movie(self, id: str) -> Optional[MovieMetadata]:
        # Support either tmdb id (digits) or imdb id (tt...)
        tmdb_id = id
        if id.startswith("tt"):
            find_resp = self.client.get(
                f"{self.BASE_URL}/find/{id}",
                params={"api_key": self.api_key, "external_source": "imdb_id"},
            )
            if find_resp.status_code == 200:
                results = find_resp.json().get("movie_results", [])
                if results:
                    tmdb_id = str(results[0]["id"])
                else:
                    return None
            else:
                return None

        try:
            resp = self.client.get(
                f"{self.BASE_URL}/movie/{tmdb_id}",
                params={"api_key": self.api_key, "append_to_response": "credits,images,external_ids,keywords"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        title = data.get("title")
        original_title = data.get("original_title")
        release_date = data.get("release_date")
        year = int(release_date[:4]) if release_date and len(release_date) >= 4 else None
        plot = data.get("overview")
        tagline = data.get("tagline")
        runtime = data.get("runtime")

        ratings: list[Rating] = []
        vote_avg = data.get("vote_average")
        vote_count = data.get("vote_count", 0)
        if vote_avg:
            ratings.append(
                Rating(name="themoviedb", value=float(vote_avg), votes=int(vote_count), max_value=10, is_default=False)
            )

        genres = [g["name"] for g in data.get("genres", []) if "name" in g]
        studios = [c["name"] for c in data.get("production_companies", []) if "name" in c]
        countries = [c["name"] for c in data.get("production_countries", []) if "name" in c]

        # Extract tags from TMDB keywords
        raw_keywords = data.get("keywords", {}).get("keywords", [])
        tags = [kw["name"] for kw in raw_keywords if kw.get("name")]

        external_ids = data.get("external_ids", {})
        imdb_id = external_ids.get("imdb_id") or data.get("imdb_id")

        # Cast & Crew
        credits_data = data.get("credits", {})
        actors: list[Person] = []
        for cast_member in credits_data.get("cast", [])[:20]:
            p_img = f"{self.IMG_BASE_URL}{cast_member['profile_path']}" if cast_member.get("profile_path") else None
            actors.append(
                Person(
                    name=cast_member.get("name"),
                    role=cast_member.get("character"),
                    person_type="Actor",
                    thumb=p_img,
                    tmdb_id=str(cast_member.get("id")) if cast_member.get("id") else None,
                )
            )

        directors: list[Person] = []
        writers: list[Person] = []
        producers: list[Person] = []

        for crew_member in credits_data.get("crew", []):
            job = crew_member.get("job")
            p_id = str(crew_member.get("id")) if crew_member.get("id") else None
            p_name = crew_member.get("name")
            p_thumb = f"{self.IMG_BASE_URL}{crew_member['profile_path']}" if crew_member.get("profile_path") else None

            if job == "Director":
                directors.append(Person(name=p_name, person_type="Director", tmdb_id=p_id, thumb=p_thumb))
            elif job in ("Screenplay", "Writer"):
                writers.append(Person(name=p_name, person_type="Writer", tmdb_id=p_id, thumb=p_thumb))
            elif job == "Producer":
                producers.append(Person(name=p_name, person_type="Producer", tmdb_id=p_id, thumb=p_thumb))

        posters: list[str] = []
        fanarts: list[str] = []

        poster_path = data.get("poster_path")
        if poster_path:
            posters.append(f"{self.IMG_BASE_URL}{poster_path}")

        backdrop_path = data.get("backdrop_path")
        if backdrop_path:
            fanarts.append(f"{self.IMG_BASE_URL}{backdrop_path}")

        images_data = data.get("images", {})
        for bp in images_data.get("backdrops", [])[:5]:
            f_url = f"{self.IMG_BASE_URL}{bp['file_path']}"
            if f_url not in fanarts:
                fanarts.append(f_url)

        return MovieMetadata(
            title=title,
            original_title=original_title,
            year=year,
            premiered=release_date,
            plot=plot,
            outline=plot,
            tagline=tagline,
            runtime=runtime,
            ratings=ratings,
            genres=genres,
            studios=studios,
            countries=countries,
            imdb_id=imdb_id,
            tmdb_id=str(data["id"]),
            tags=tags,
            actors=actors,
            directors=directors,
            writers=writers,
            producers=producers,
            posters=posters,
            fanarts=fanarts,
        )

    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        params = {"api_key": self.api_key, "query": query}
        if year:
            params["first_air_date_year"] = str(year)

        try:
            resp = self.client.get(f"{self.BASE_URL}/search/tv", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            return []

        search_results: list[SearchResult] = []
        for r in results:
            r_id = str(r.get("id"))
            title = r.get("name")
            air_date = r.get("first_air_date")
            r_year = int(air_date[:4]) if air_date and len(air_date) >= 4 else None
            overview = r.get("overview")
            poster_path = r.get("poster_path")
            poster_url = f"{self.IMG_BASE_URL}{poster_path}" if poster_path else None

            search_results.append(
                SearchResult(
                    id=r_id,
                    title=title,
                    year=r_year,
                    media_type="tv",
                    overview=overview,
                    poster_url=poster_url,
                    source=self.name,
                )
            )
        return search_results

    def get_tvshow(self, id: str) -> Optional[TVShowMetadata]:
        tmdb_id = id
        if id.startswith("tt"):
            find_resp = self.client.get(
                f"{self.BASE_URL}/find/{id}",
                params={"api_key": self.api_key, "external_source": "imdb_id"},
            )
            if find_resp.status_code == 200:
                results = find_resp.json().get("tv_results", [])
                if results:
                    tmdb_id = str(results[0]["id"])
                else:
                    return None
            else:
                return None

        try:
            resp = self.client.get(
                f"{self.BASE_URL}/tv/{tmdb_id}",
                params={"api_key": self.api_key, "append_to_response": "credits,images,external_ids,keywords"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return None

        title = data.get("name")
        original_title = data.get("original_name")
        first_air = data.get("first_air_date")
        year = int(first_air[:4]) if first_air and len(first_air) >= 4 else None
        plot = data.get("overview")
        status = data.get("status")

        ratings: list[Rating] = []
        vote_avg = data.get("vote_average")
        vote_count = data.get("vote_count", 0)
        if vote_avg:
            ratings.append(
                Rating(name="themoviedb", value=float(vote_avg), votes=int(vote_count), max_value=10, is_default=False)
            )

        genres = [g["name"] for g in data.get("genres", []) if "name" in g]
        studios = [c["name"] for c in data.get("production_companies", []) if "name" in c]
        for net in data.get("networks", []):
            if net.get("name") and net["name"] not in studios:
                studios.append(net["name"])
        countries = data.get("origin_country", [])

        external_ids = data.get("external_ids", {})
        imdb_id = external_ids.get("imdb_id")
        tvdb_id = str(external_ids.get("tvdb_id")) if external_ids.get("tvdb_id") else None

        # Tags from TMDB keywords
        raw_keywords = data.get("keywords", {}).get("results", [])
        tags = [kw["name"] for kw in raw_keywords if kw.get("name")]

        # Cast
        actors: list[Person] = []
        for cast_member in data.get("credits", {}).get("cast", [])[:20]:
            p_img = f"{self.IMG_BASE_URL}{cast_member['profile_path']}" if cast_member.get("profile_path") else None
            actors.append(
                Person(
                    name=cast_member.get("name"),
                    role=cast_member.get("character"),
                    person_type="Actor",
                    thumb=p_img,
                    tmdb_id=str(cast_member.get("id")) if cast_member.get("id") else None,
                )
            )

        posters: list[str] = []
        if data.get("poster_path"):
            posters.append(f"{self.IMG_BASE_URL}{data['poster_path']}")

        fanarts: list[str] = []
        if data.get("backdrop_path"):
            fanarts.append(f"{self.IMG_BASE_URL}{data['backdrop_path']}")

        return TVShowMetadata(
            title=title,
            original_title=original_title,
            plot=plot,
            outline=plot,
            year=year,
            premiered=first_air,
            status=status,
            ratings=ratings,
            genres=genres,
            studios=studios,
            countries=countries,
            imdb_id=imdb_id,
            tvdb_id=tvdb_id,
            tmdb_id=str(data["id"]),
            official_website=data.get("homepage"),
            tags=tags,
            actors=actors,
            posters=posters,
            fanarts=fanarts,
        )
