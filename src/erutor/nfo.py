"""NFO generation engine producing Kodi / Jellyfin / Emby compliant XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from erutor.models import (
    EpisodeMetadata,
    FileInfo,
    MovieMetadata,
    Person,
    Rating,
    SeasonMetadata,
    TVShowMetadata,
)


def _add_sub_element(parent: ET.Element, tag: str, text: Optional[str] = None, **attribs) -> ET.Element:
    """Helper to add an XML sub-element if text is not None, or empty element if explicitly allowed."""
    elem = ET.SubElement(parent, tag, **{k: str(v) for k, v in attribs.items() if v is not None})
    if text is not None:
        elem.text = str(text)
    return elem


def _append_ratings(parent: ET.Element, ratings: list[Rating]) -> None:
    if not ratings:
        return
    ratings_elem = ET.SubElement(parent, "ratings")
    for r in ratings:
        attrib = {
            "name": r.name,
            "max": str(r.max_value),
            "default": "true" if r.is_default else "false",
        }
        r_elem = ET.SubElement(ratings_elem, "rating", **attrib)
        _add_sub_element(r_elem, "value", f"{r.value:.1f}")
        _add_sub_element(r_elem, "votes", str(r.votes))


def _append_person(parent: ET.Element, tag: str, person: Person) -> None:
    attrib = {}
    if person.tmdb_id:
        attrib["tmdbid"] = person.tmdb_id
    if person.tvdb_id:
        attrib["tvdbid"] = person.tvdb_id
    if person.imdb_id:
        attrib["imdbid"] = person.imdb_id

    if tag == "actor":
        elem = ET.SubElement(parent, "actor")
        _add_sub_element(elem, "name", person.name)
        if person.role:
            _add_sub_element(elem, "role", person.role)
        _add_sub_element(elem, "type", person.person_type or "Actor")
        if person.thumb:
            _add_sub_element(elem, "thumb", person.thumb)
        if person.profile:
            _add_sub_element(elem, "profile", person.profile)
        if person.tmdb_id:
            _add_sub_element(elem, "tmdbid", person.tmdb_id)
        if person.tvdb_id:
            _add_sub_element(elem, "tvdbid", person.tvdb_id)
        if person.imdb_id:
            _add_sub_element(elem, "imdbid", person.imdb_id)
    elif tag == "producer":
        elem = ET.SubElement(parent, "producer", **attrib)
        _add_sub_element(elem, "name", person.name)
        if person.role:
            _add_sub_element(elem, "role", person.role)
        if person.profile:
            _add_sub_element(elem, "profile", person.profile)
    else:
        # director, writer, credits
        elem = ET.SubElement(parent, tag, **attrib)
        elem.text = person.name


def _append_file_info(parent: ET.Element, file_info: Optional[FileInfo]) -> None:
    if not file_info:
        return
    fi_elem = ET.SubElement(parent, "fileinfo")
    sd_elem = ET.SubElement(fi_elem, "streamdetails")

    if file_info.video:
        v = file_info.video
        v_elem = ET.SubElement(sd_elem, "video")
        if v.codec:
            _add_sub_element(v_elem, "codec", v.codec)
        if v.aspect:
            _add_sub_element(v_elem, "aspect", v.aspect)
        if v.width:
            _add_sub_element(v_elem, "width", str(v.width))
        if v.height:
            _add_sub_element(v_elem, "height", str(v.height))
        if v.duration_seconds:
            _add_sub_element(v_elem, "durationinseconds", str(v.duration_seconds))
        if v.bitrate:
            _add_sub_element(v_elem, "bitrate", str(v.bitrate))
        if v.framerate:
            _add_sub_element(v_elem, "framerate", str(v.framerate))

    for a in file_info.audio:
        a_elem = ET.SubElement(sd_elem, "audio")
        if a.codec:
            _add_sub_element(a_elem, "codec", a.codec)
        if a.language:
            _add_sub_element(a_elem, "language", a.language)
        if a.channels:
            _add_sub_element(a_elem, "channels", str(a.channels))
        if a.bitrate:
            _add_sub_element(a_elem, "bitrate", str(a.bitrate))
        if a.sampling_rate:
            _add_sub_element(a_elem, "samplingrate", str(a.sampling_rate))

    for s in file_info.subtitles:
        s_elem = ET.SubElement(sd_elem, "subtitle")
        if s.language:
            _add_sub_element(s_elem, "language", s.language)


def _to_xml_string(root: ET.Element) -> str:
    """Format and pretty-print XML with declaration."""
    ET.indent(root, space="  ", level=0)
    xml_data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_data.decode("utf-8") + "\n"


class NFOBuilder:
    """Builds Kodi/Jellyfin/Emby compatible XML NFOs."""

    @staticmethod
    def build_movie_nfo(movie: MovieMetadata) -> str:
        root = ET.Element("movie")

        _add_sub_element(root, "title", movie.title)
        _add_sub_element(root, "originaltitle", movie.original_title or movie.title)
        if movie.sort_title:
            _add_sub_element(root, "sorttitle", movie.sort_title)

        if movie.year:
            _add_sub_element(root, "year", str(movie.year))

        _append_ratings(root, movie.ratings)

        if movie.user_rating is not None:
            _add_sub_element(root, "userrating", str(movie.user_rating))
        if movie.top250 is not None:
            _add_sub_element(root, "top250", str(movie.top250))

        if movie.plot:
            _add_sub_element(root, "plot", movie.plot)
        if movie.outline:
            _add_sub_element(root, "outline", movie.outline)
        if movie.tagline:
            _add_sub_element(root, "tagline", movie.tagline)

        if movie.runtime:
            _add_sub_element(root, "runtime", str(movie.runtime))

        for poster in movie.posters:
            _add_sub_element(root, "thumb", poster, aspect="poster")

        if movie.fanarts:
            fanart_elem = ET.SubElement(root, "fanart")
            for fa in movie.fanarts:
                _add_sub_element(fanart_elem, "thumb", fa)

        if movie.mpaa:
            _add_sub_element(root, "mpaa", movie.mpaa)
        if movie.certification:
            _add_sub_element(root, "certification", movie.certification)

        # IDs
        primary_id = movie.imdb_id or movie.tmdb_id or movie.tvdb_id
        if primary_id:
            _add_sub_element(root, "id", primary_id)
        if movie.tmdb_id:
            _add_sub_element(root, "tmdbid", movie.tmdb_id)
            _add_sub_element(root, "uniqueid", movie.tmdb_id, type="tmdb", default="false")
        if movie.imdb_id:
            _add_sub_element(root, "uniqueid", movie.imdb_id, type="imdb", default="true")
        if movie.tvdb_id:
            _add_sub_element(root, "tvdbid", movie.tvdb_id)
            _add_sub_element(root, "uniqueid", movie.tvdb_id, type="tvdb", default="false")
        if movie.official_website:
            _add_sub_element(root, "uniqueid", movie.official_website, type="official website", default="false")

        for country in movie.countries:
            _add_sub_element(root, "country", country)

        if movie.premiered:
            _add_sub_element(root, "premiered", movie.premiered)

        for genre in movie.genres:
            _add_sub_element(root, "genre", genre)

        for studio in movie.studios:
            _add_sub_element(root, "studio", studio)

        for writer in movie.writers:
            _append_person(root, "credits", writer)
            _append_person(root, "writer", writer)

        for director in movie.directors:
            _append_person(root, "director", director)

        for tag in movie.tags:
            _add_sub_element(root, "tag", tag)

        for actor in movie.actors:
            _append_person(root, "actor", actor)

        for producer in movie.producers:
            _append_person(root, "producer", producer)

        if movie.trailer:
            _add_sub_element(root, "trailer", movie.trailer)

        if movie.languages:
            _add_sub_element(root, "languages", ", ".join(movie.languages))

        if movie.date_added:
            _add_sub_element(root, "dateadded", movie.date_added)

        _append_file_info(root, movie.file_info)

        if movie.source:
            _add_sub_element(root, "source", movie.source)
        if movie.edition:
            _add_sub_element(root, "edition", movie.edition)
        if movie.original_filename:
            _add_sub_element(root, "original_filename", movie.original_filename)

        return _to_xml_string(root)

    @staticmethod
    def build_tvshow_nfo(show: TVShowMetadata) -> str:
        root = ET.Element("tvshow")

        _add_sub_element(root, "title", show.title)
        _add_sub_element(root, "originaltitle", show.original_title or show.title)
        _add_sub_element(root, "showtitle", show.title)

        if show.plot:
            _add_sub_element(root, "plot", show.plot)
        if show.outline:
            _add_sub_element(root, "outline", show.outline or show.plot)

        _add_sub_element(root, "lockdata", "false")
        if show.date_added:
            _add_sub_element(root, "dateadded", show.date_added)

        if show.runtime:
            _add_sub_element(root, "runtime", str(show.runtime))

        for country in show.countries:
            _add_sub_element(root, "country", country)

        for genre in show.genres:
            _add_sub_element(root, "genre", genre)

        for studio in show.studios:
            _add_sub_element(root, "studio", studio)

        for tag in show.tags:
            _add_sub_element(root, "tag", tag)

        # Unique IDs
        if show.tvdb_id:
            _add_sub_element(root, "uniqueid", show.tvdb_id, type="tvdb")
            _add_sub_element(root, "tvdbid", show.tvdb_id)
        if show.imdb_id:
            _add_sub_element(root, "uniqueid", show.imdb_id, type="imdb")
        if show.tmdb_id:
            _add_sub_element(root, "uniqueid", show.tmdb_id, type="tmdb")
            _add_sub_element(root, "tmdbid", show.tmdb_id)
        if show.official_website:
            _add_sub_element(root, "uniqueid", show.official_website, type="official website")

        primary_id = show.tvdb_id or show.imdb_id or show.tmdb_id
        if primary_id:
            _add_sub_element(root, "id", primary_id)

        _add_sub_element(root, "season", "-1")
        _add_sub_element(root, "episode", "-1")
        _add_sub_element(root, "displayorder", "aired")

        if show.status:
            _add_sub_element(root, "status", show.status)

        _append_ratings(root, show.ratings)

        for poster in show.posters:
            _add_sub_element(root, "thumb", poster, aspect="poster")

        for banner in show.banners:
            _add_sub_element(root, "thumb", banner, aspect="banner")

        for s_num, name in show.named_seasons.items():
            _add_sub_element(root, "namedseason", name, number=str(s_num))

        for s_num, s_posters in show.season_posters.items():
            for sp in s_posters:
                _add_sub_element(root, "thumb", sp, aspect="poster", season=str(s_num), type="season")

        for s_num, s_banners in show.season_banners.items():
            for sb in s_banners:
                _add_sub_element(root, "thumb", sb, aspect="banner", season=str(s_num), type="season")

        for s_num, s_thumbs in show.season_thumbs.items():
            for st in s_thumbs:
                _add_sub_element(root, "thumb", st, aspect="thumb", season=str(s_num), type="season")

        if show.fanarts:
            fanart_elem = ET.SubElement(root, "fanart")
            for fa in show.fanarts:
                _add_sub_element(fanart_elem, "thumb", fa)

        if show.mpaa:
            _add_sub_element(root, "mpaa", show.mpaa)
        if show.certification:
            _add_sub_element(root, "certification", show.certification)

        for actor in show.actors:
            _append_person(root, "actor", actor)

        return _to_xml_string(root)

    @staticmethod
    def build_season_nfo(season: SeasonMetadata) -> str:
        root = ET.Element("season")

        if season.plot:
            _add_sub_element(root, "plot", season.plot)
        if season.outline:
            _add_sub_element(root, "outline", season.outline or season.plot)

        _add_sub_element(root, "lockdata", "false")
        if season.date_added:
            _add_sub_element(root, "dateadded", season.date_added)

        title = season.title or f"Season {season.season_number}"
        _add_sub_element(root, "title", title)

        if season.year:
            _add_sub_element(root, "year", str(season.year))

        _add_sub_element(root, "sorttitle", f"{season.season_number:04d}")

        if season.premiered:
            _add_sub_element(root, "premiered", season.premiered)
        if season.release_date:
            _add_sub_element(root, "releasedate", season.release_date)

        _add_sub_element(root, "seasonnumber", str(season.season_number))

        for tag in season.tags:
            _add_sub_element(root, "tag", tag)

        for poster in season.posters:
            _add_sub_element(root, "thumb", poster, aspect="poster")

        return _to_xml_string(root)

    @staticmethod
    def build_episode_nfo(episode: EpisodeMetadata) -> str:
        root = ET.Element("episodedetails")

        _add_sub_element(root, "title", episode.title)
        _add_sub_element(root, "originaltitle", episode.original_title or episode.title)
        if episode.show_title:
            _add_sub_element(root, "showtitle", episode.show_title)

        _add_sub_element(root, "season", str(episode.season_number))
        _add_sub_element(root, "episode", str(episode.episode_number))

        if episode.plot:
            _add_sub_element(root, "plot", episode.plot)
        if episode.outline:
            _add_sub_element(root, "outline", episode.outline)

        _add_sub_element(root, "lockdata", "false")
        if episode.date_added:
            _add_sub_element(root, "dateadded", episode.date_added)

        if episode.aired:
            _add_sub_element(root, "aired", episode.aired)
        if episode.year:
            _add_sub_element(root, "year", str(episode.year))

        if episode.runtime:
            _add_sub_element(root, "runtime", str(episode.runtime))

        _append_ratings(root, episode.ratings)

        if episode.mpaa:
            _add_sub_element(root, "mpaa", episode.mpaa)

        # IDs
        if episode.imdb_id:
            _add_sub_element(root, "imdbid", episode.imdb_id)
            _add_sub_element(root, "uniqueid", episode.imdb_id, type="imdb")
        if episode.tvdb_id:
            _add_sub_element(root, "tvdbid", episode.tvdb_id)
            _add_sub_element(root, "uniqueid", episode.tvdb_id, type="tvdb")
        if episode.tmdb_id:
            _add_sub_element(root, "tmdbid", episode.tmdb_id)
            _add_sub_element(root, "uniqueid", episode.tmdb_id, type="tmdb")

        for genre in episode.genres:
            _add_sub_element(root, "genre", genre)

        for studio in episode.studios:
            _add_sub_element(root, "studio", studio)

        for tag in episode.tags:
            _add_sub_element(root, "tag", tag)

        for writer in episode.writers:
            _append_person(root, "writer", writer)
            _append_person(root, "credits", writer)

        for director in episode.directors:
            _append_person(root, "director", director)

        for actor in episode.actors:
            _append_person(root, "actor", actor)

        if episode.thumbnail_url:
            _add_sub_element(root, "thumb", episode.thumbnail_url)

        _append_file_info(root, episode.file_info)

        if episode.source:
            _add_sub_element(root, "source", episode.source)
        if episode.original_filename:
            _add_sub_element(root, "original_filename", episode.original_filename)

        return _to_xml_string(root)
