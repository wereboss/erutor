"""TVMaze API fetcher for TV shows (100% free, no API key required)."""

from __future__ import annotations

import re
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


def _strip_html(html_str: Optional[str]) -> Optional[str]:
    if not html_str:
        return None
    clean = re.sub(r"<[^>]+>", "", html_str).strip()
    return clean if clean else None


class TVMazeFetcher(BaseFetcher):
    """Fetcher for TV shows using the free TVMaze REST API."""

    name = "tvmaze"
    BASE_URL = "https://api.tvmaze.com"

    def __init__(self, client: Optional[httpx.Client] = None):
        self.client = client or httpx.Client(
            headers={"User-Agent": "Erutor/0.1 (https://github.com/erutor)"},
            timeout=15.0,
        )

    def search_movie(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        # TVMaze is TV shows only
        return []

    def get_movie(self, id: str) -> Optional[MovieMetadata]:
        return None

    def search_tv(self, query: str, year: Optional[int] = None) -> list[SearchResult]:
        url = f"{self.BASE_URL}/search/shows"
        try:
            resp = self.client.get(url, params={"q": query})
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        results: list[SearchResult] = []
        for item in data:
            show = item.get("show", {})
            show_id = str(show.get("id"))
            name = show.get("name")
            premiered = show.get("premiered")
            show_year = int(premiered[:4]) if premiered and len(premiered) >= 4 else None

            if year and show_year and abs(year - show_year) > 1:
                # Year mismatch
                continue

            summary = _strip_html(show.get("summary"))
            image_obj = show.get("image") or {}
            poster_url = image_obj.get("original") or image_obj.get("medium")

            results.append(
                SearchResult(
                    id=show_id,
                    title=name,
                    year=show_year,
                    media_type="tv",
                    overview=summary,
                    poster_url=poster_url,
                    source=self.name,
                )
            )
        return results

    def get_tvshow(self, id: str) -> Optional[TVShowMetadata]:
        clean_id = id.strip()
        # Handle explicit prefixes
        if clean_id.lower().startswith("tvdb:") or clean_id.lower().startswith("thetvdb:"):
            tvdb_num = clean_id.split(":")[-1].strip()
            try:
                resp = self.client.get(f"{self.BASE_URL}/lookup/shows", params={"thetvdb": tvdb_num}, follow_redirects=True)
                if resp.status_code == 200:
                    clean_id = str(resp.json().get("id"))
                else:
                    return None
            except Exception:
                return None
        elif clean_id.lower().startswith("imdb:"):
            clean_id = clean_id.split(":")[-1].strip()

        # If clean_id starts with 'tt' (IMDb ID), use TVMaze lookup
        if clean_id.startswith("tt"):
            lookup_url = f"{self.BASE_URL}/lookup/shows"
            try:
                resp = self.client.get(lookup_url, params={"imdb": clean_id}, follow_redirects=True)
                resp.raise_for_status()
                show_data = resp.json()
                clean_id = str(show_data.get("id"))
            except Exception:
                return None

        url = f"{self.BASE_URL}/shows/{clean_id}"
        data = None
        try:
            resp = self.client.get(url, params={"embed[]": ["episodes", "cast", "seasons"]})
            if resp.status_code == 200:
                data = resp.json()
            elif resp.status_code == 404 and clean_id.isdigit():
                # Fallback: maybe clean_id was a TheTVDB ID
                lookup_resp = self.client.get(f"{self.BASE_URL}/lookup/shows", params={"thetvdb": clean_id}, follow_redirects=True)
                if lookup_resp.status_code == 200:
                    resolved_id = str(lookup_resp.json().get("id"))
                    retry_resp = self.client.get(f"{self.BASE_URL}/shows/{resolved_id}", params={"embed[]": ["episodes", "cast", "seasons"]})
                    if retry_resp.status_code == 200:
                        data = retry_resp.json()
        except Exception:
            return None

        if not data:
            return None


        title = data.get("name", "Unknown Title")
        premiered = data.get("premiered")
        year = int(premiered[:4]) if premiered and len(premiered) >= 4 else None
        summary = _strip_html(data.get("summary"))
        status = data.get("status")
        runtime = data.get("averageRuntime") or data.get("runtime")

        ratings: list[Rating] = []
        rating_val = (data.get("rating") or {}).get("average")
        if rating_val:
            ratings.append(Rating(name="tvmaze", value=float(rating_val), max_value=10, is_default=True))

        genres = data.get("genres") or []
        studios: list[str] = []
        countries: list[str] = []

        network = data.get("network")
        if network:
            if network.get("name"):
                studios.append(network["name"])
            if network.get("country") and network["country"].get("name"):
                countries.append(network["country"]["name"])

        web_channel = data.get("webChannel")
        if web_channel and web_channel.get("name"):
            studios.append(web_channel["name"])

        externals = data.get("externals") or {}
        imdb_id = externals.get("imdb")
        tvdb_id = str(externals.get("thetvdb")) if externals.get("thetvdb") else None
        official_site = data.get("officialSite")

        posters: list[str] = []
        image_obj = data.get("image") or {}
        if image_obj.get("original"):
            posters.append(image_obj["original"])

        embedded = data.get("_embedded") or {}

        # Parse Cast
        actors: list[Person] = []
        for c in embedded.get("cast") or []:
            person_obj = c.get("person") or {}
            char_obj = c.get("character") or {}
            p_img = (person_obj.get("image") or {}).get("original")
            actors.append(
                Person(
                    name=person_obj.get("name", "Unknown"),
                    role=char_obj.get("name"),
                    person_type="Actor",
                    thumb=p_img,
                )
            )

        # Detect and map year-based or non-sequential season numbers (e.g. Columbo: 1968, 1971...)
        raw_seasons = embedded.get("seasons") or []
        raw_episodes = embedded.get("episodes") or []

        all_season_nums = set()
        for s in raw_seasons:
            if s.get("number") is not None and s.get("number") > 0:
                all_season_nums.add(s["number"])
        for ep in raw_episodes:
            if ep.get("season") is not None and ep.get("season") > 0:
                all_season_nums.add(ep["season"])

        has_year_seasons = any(n >= 1000 for n in all_season_nums)
        season_map: dict[int, int] = {}
        if has_year_seasons:
            sorted_nums = sorted(all_season_nums)
            for idx, old_n in enumerate(sorted_nums, start=1):
                season_map[old_n] = idx
            season_map[0] = 0

        # Parse Seasons
        seasons_meta: list[SeasonMetadata] = []
        season_posters: dict[int, list[str]] = {}
        named_seasons: dict[int, str] = {}

        for s in raw_seasons:
            raw_num = s.get("number")
            if raw_num is None:
                continue
            s_num = season_map.get(raw_num, raw_num)

            s_name = s.get("name")
            if s_name:
                named_seasons[s_num] = s_name

            s_summary = _strip_html(s.get("summary"))
            s_prem = s.get("premiereDate")
            if raw_num >= 1000:
                s_year = raw_num
            elif s_prem and len(s_prem) >= 4:
                s_year = int(s_prem[:4])
            else:
                s_year = year

            s_img_obj = s.get("image") or {}
            s_poster = s_img_obj.get("original") or s_img_obj.get("medium")
            s_posters = [s_poster] if s_poster else []

            if s_posters:
                season_posters[s_num] = s_posters

            seasons_meta.append(
                SeasonMetadata(
                    season_number=s_num,
                    title=s_name or f"Season {s_num}",
                    plot=s_summary,
                    outline=s_summary,
                    year=s_year,
                    premiered=s_prem,
                    release_date=s_prem,
                    posters=s_posters,
                )
            )

        # Parse Episodes
        episodes_meta: list[EpisodeMetadata] = []
        for ep in raw_episodes:
            raw_season = ep.get("season")
            ep_number = ep.get("number")
            if raw_season is None or ep_number is None:
                continue

            ep_season = season_map.get(raw_season, raw_season)
            ep_title = ep.get("name") or f"Episode {ep_number}"
            ep_aired = ep.get("airdate")
            ep_year = int(ep_aired[:4]) if ep_aired and len(ep_aired) >= 4 else year
            ep_plot = _strip_html(ep.get("summary"))
            ep_runtime = ep.get("runtime") or runtime

            ep_ratings: list[Rating] = []
            ep_r_val = (ep.get("rating") or {}).get("average")
            if ep_r_val:
                ep_ratings.append(Rating(name="tvmaze", value=float(ep_r_val), max_value=10, is_default=True))

            ep_img_obj = ep.get("image") or {}
            ep_thumb = ep_img_obj.get("original") or ep_img_obj.get("medium")

            episodes_meta.append(
                EpisodeMetadata(
                    title=ep_title,
                    season_number=ep_season,
                    episode_number=ep_number,
                    show_title=title,
                    plot=ep_plot,
                    outline=ep_plot,
                    aired=ep_aired,
                    year=ep_year,
                    runtime=ep_runtime,
                    ratings=ep_ratings,
                    genres=genres,
                    studios=studios,
                    actors=actors[:10],  # Main recurring cast
                    thumbnail_url=ep_thumb,
                )
            )


        return TVShowMetadata(
            title=title,
            original_title=title,
            plot=summary,
            outline=summary,
            year=year,
            premiered=premiered,
            status=status,
            runtime=runtime,
            ratings=ratings,
            genres=genres,
            studios=studios,
            countries=countries,
            imdb_id=imdb_id,
            tvdb_id=tvdb_id,
            official_website=official_site,
            actors=actors,
            posters=posters,
            named_seasons=named_seasons,
            season_posters=season_posters,
            seasons=seasons_meta,
            episodes=episodes_meta,
        )
