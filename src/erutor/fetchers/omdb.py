"""OMDb API fetcher for ratings, movie/show metadata, and posters."""

from __future__ import annotations

import re
from typing import Optional

import httpx

from erutor.fetchers.base import BaseFetcher
from erutor.models import MovieMetadata, Person, Rating, SearchResult, TVShowMetadata


class OMDbFetcher(BaseFetcher):
    """Fetcher for movies and TV shows using OMDb API."""

    name = "omdb"
    BASE_URL = "http://www.omdbapi.com"

    def __init__(self, api_key: str, client: Optional[httpx.Client] = None):
        self.api_key = api_key
        self.client = client or httpx.Client(
            headers={"User-Agent": "Erutor/0.1 (https://github.com/erutor)"},
            timeout=15.0,
        )

    def search_movie(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        params = {"apikey": self.api_key, "s": query, "type": "movie"}
        if year:
            params["y"] = str(year)

        try:
            resp = self.client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("Response") != "True":
                return []
            items = data.get("Search", [])
        except Exception:
            return []

        results: list[SearchResult] = []
        for item in items:
            item_year = int(item["Year"][:4]) if "Year" in item and item["Year"][:4].isdigit() else None
            poster = item.get("Poster")
            poster_url = poster if poster and poster != "N/A" else None
            results.append(
                SearchResult(
                    id=item.get("imdbID", ""),
                    title=item.get("Title", ""),
                    year=item_year,
                    media_type="movie",
                    poster_url=poster_url,
                    source=self.name,
                )
            )
        return results

    def get_movie(self, id: str) -> Optional[MovieMetadata]:
        params = {"apikey": self.api_key, "i": id, "plot": "full"}
        try:
            resp = self.client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("Response") != "True":
                return None
        except Exception:
            return None

        title = data.get("Title", "Unknown")
        year_str = data.get("Year", "")
        year = int(year_str[:4]) if year_str[:4].isdigit() else None
        premiered = data.get("Released")
        plot = data.get("Plot") if data.get("Plot") != "N/A" else None

        runtime_match = re.search(r"(\d+)\s*min", data.get("Runtime", ""))
        runtime = int(runtime_match.group(1)) if runtime_match else None

        ratings: list[Rating] = []
        # Parse IMDb rating
        imdb_rating = data.get("imdbRating")
        imdb_votes = data.get("imdbVotes", "0").replace(",", "")
        if imdb_rating and imdb_rating != "N/A":
            ratings.append(
                Rating(
                    name="imdb",
                    value=float(imdb_rating),
                    votes=int(imdb_votes) if imdb_votes.isdigit() else 0,
                    max_value=10,
                    is_default=True,
                )
            )

        # Parse Rotten Tomatoes and Metacritic
        for r in data.get("Ratings", []):
            source = r.get("Source", "")
            val_str = r.get("Value", "")
            if source == "Rotten Tomatoes" and "%" in val_str:
                val = float(val_str.replace("%", "").strip())
                ratings.append(Rating(name="tomatometerallcritics", value=val, max_value=100, is_default=False))
            elif source == "Metacritic" and "/" in val_str:
                val = float(val_str.split("/")[0].strip())
                ratings.append(Rating(name="metascore", value=val, max_value=100, is_default=False))

        genres = [g.strip() for g in data.get("Genre", "").split(",") if g.strip() and g.strip() != "N/A"]
        countries = [c.strip() for c in data.get("Country", "").split(",") if c.strip() and c.strip() != "N/A"]
        languages = [lang.strip() for lang in data.get("Language", "").split(",") if lang.strip() and lang.strip() != "N/A"]

        mpaa = data.get("Rated") if data.get("Rated") != "N/A" else None

        actors = [
            Person(name=a.strip(), person_type="Actor")
            for a in data.get("Actors", "").split(",")
            if a.strip() and a.strip() != "N/A"
        ]
        directors = [
            Person(name=d.strip(), person_type="Director")
            for d in data.get("Director", "").split(",")
            if d.strip() and d.strip() != "N/A"
        ]
        writers = [
            Person(name=w.strip(), person_type="Writer")
            for w in data.get("Writer", "").split(",")
            if w.strip() and w.strip() != "N/A"
        ]

        posters = []
        p = data.get("Poster")
        if p and p != "N/A":
            posters.append(p)

        tags = []
        if data.get("Type") and data.get("Type") != "N/A":
            tags.append(data.get("Type").lower())

        return MovieMetadata(
            title=title,
            original_title=title,
            year=year,
            premiered=premiered,
            plot=plot,
            outline=plot,
            runtime=runtime,
            ratings=ratings,
            genres=genres,
            countries=countries,
            languages=languages,
            mpaa=mpaa,
            certification=mpaa,
            imdb_id=data.get("imdbID"),
            tags=tags,
            actors=actors,
            directors=directors,
            writers=writers,
            posters=posters,
        )

    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        return []

    def get_tvshow(self, id: str) -> Optional[TVShowMetadata]:
        return None
