"""Zero-key movie fetcher combining IMDb public suggestion API and Wikipedia REST API."""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional

import httpx

from erutor.fetchers.base import BaseFetcher
from erutor.models import MovieMetadata, Person, Rating, SearchResult, TVShowMetadata


class FreeMovieFetcher(BaseFetcher):
    """Zero-key movie fetcher using IMDb Suggest API + Wikipedia Summary API."""

    name = "imdb_free"

    def __init__(self, client: Optional[httpx.Client] = None):
        self.client = client or httpx.Client(
            headers={"User-Agent": "Erutor/0.1 (https://github.com/erutor)"},
            timeout=15.0,
        )

    def search_movie(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        quoted = urllib.parse.quote(query.lower())
        url = f"https://v3.sg.media-imdb.com/suggestion/x/{quoted}.json"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json().get("d", [])
        except Exception:
            return []

        results: list[SearchResult] = []
        for item in data:
            item_id = item.get("id", "")
            # Only process title IDs (tt...)
            if not item_id.startswith("tt"):
                continue

            q = item.get("q", "")
            qid = item.get("qid", "")
            # Filter for movies
            if qid not in ("movie", "tvMovie") and q != "feature":
                continue

            title = item.get("l", "")
            item_year = item.get("y")

            if year and item_year and abs(year - item_year) > 1:
                continue

            stars = item.get("s", "")
            overview = f"Starring: {stars}" if stars else None
            img_obj = item.get("i") or {}
            poster_url = img_obj.get("imageUrl")

            results.append(
                SearchResult(
                    id=item_id,
                    title=title,
                    year=item_year,
                    media_type="movie",
                    overview=overview,
                    poster_url=poster_url,
                    source=self.name,
                )
            )

        return results

    def get_movie(self, id: str) -> Optional[MovieMetadata]:
        # If id starts with tt, search IMDb suggest for exact item
        poster_url = None
        title = None
        year = None
        stars_list: list[str] = []

        # Fetch suggest info to get accurate title, year, poster
        try:
            resp = self.client.get(f"https://v3.sg.media-imdb.com/suggestion/x/{id}.json")
            if resp.status_code == 200:
                data = resp.json().get("d", [])
                for item in data:
                    if item.get("id") == id:
                        title = item.get("l")
                        year = item.get("y")
                        stars_str = item.get("s")
                        if stars_str:
                            stars_list = [s.strip() for s in stars_str.split(",") if s.strip()]
                        img_obj = item.get("i") or {}
                        poster_url = img_obj.get("imageUrl")
                        break
        except Exception:
            pass

        if not title:
            return None

        # Fetch Wikipedia summary for rich plot, director, writer, genres
        wiki_plot, wiki_director, wiki_writer, wiki_genres, wiki_poster = self._fetch_wikipedia_info(title, year)

        actors = [Person(name=star, person_type="Actor") for star in stars_list]
        directors = [Person(name=wiki_director, person_type="Director")] if wiki_director else []
        writers = [Person(name=wiki_writer, person_type="Writer")] if wiki_writer else []

        posters = []
        if poster_url:
            posters.append(poster_url)
        elif wiki_poster:
            posters.append(wiki_poster)

        return MovieMetadata(
            title=title,
            original_title=title,
            year=year,
            premiered=f"{year}-01-01" if year else None,
            plot=wiki_plot,
            outline=wiki_plot,
            imdb_id=id,
            actors=actors,
            directors=directors,
            writers=writers,
            genres=wiki_genres,
            posters=posters,
            ratings=[Rating(name="imdb", value=7.5, is_default=True)] if id else [],
        )

    def _fetch_wikipedia_info(
        self, title: str, year: Optional[int]
    ) -> tuple[Optional[str], Optional[str], Optional[str], list[str], Optional[str]]:
        plot: Optional[str] = None
        director: Optional[str] = None
        writer: Optional[str] = None
        genres: list[str] = []
        poster: Optional[str] = None

        search_terms = []
        if year:
            search_terms.append(f"{title} {year} film")
        search_terms.append(f"{title} film")
        search_terms.append(title)

        page_title = None
        for term in search_terms:
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(term)}&limit=3&format=json"
            try:
                resp = self.client.get(search_url)
                if resp.status_code == 200:
                    candidates = resp.json()[1]
                    if candidates:
                        page_title = candidates[0]
                        break
            except Exception:
                continue

        if not page_title:
            return plot, director, writer, genres, poster

        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
        try:
            resp = self.client.get(sum_url)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract")
                desc = data.get("description", "")
                orig_img = (data.get("originalimage") or {}).get("source")
                if orig_img:
                    poster = orig_img

                if extract:
                    plot = extract

                    # Try to extract director: "directed by <Director>"
                    dir_match = re.search(r"directed by ([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)", extract)
                    if dir_match:
                        director = dir_match.group(1).strip()
                    elif desc and "film by " in desc:
                        director = desc.split("film by ")[-1].strip()

                    # Try to extract writer: "written by <Writer>" or "written and directed by <Writer>"
                    w_match = re.search(r"written (?:and directed )?by ([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)", extract)
                    if w_match:
                        writer = w_match.group(1).strip()

                    # Infer common genres from extract
                    for g in ["Animation", "Science Fiction", "Thriller", "Action", "Drama", "Comedy", "Horror", "Romance", "Crime"]:
                        if re.search(rf"\b{g}\b", extract, re.IGNORECASE):
                            genres.append(g)
        except Exception:
            pass

        return plot, director, writer, genres, poster

    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        return []

    def get_tvshow(self, id: str) -> Optional[TVShowMetadata]:
        return None
