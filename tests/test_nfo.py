"""Tests for Erutor NFO generation engine."""

import xml.etree.ElementTree as ET
from erutor.models import (
    AudioStreamDetails,
    EpisodeMetadata,
    FileInfo,
    MovieMetadata,
    Person,
    Rating,
    SeasonMetadata,
    TVShowMetadata,
    VideoStreamDetails,
)
from erutor.nfo import NFOBuilder


def test_build_movie_nfo():
    movie = MovieMetadata(
        title="A Scanner Darkly",
        original_title="A Scanner Darkly",
        sort_title="Scanner Darkly",
        year=2006,
        premiered="2006-07-07",
        plot="An undercover cop...",
        outline="An undercover cop...",
        tagline="Everything is not going to be OK.",
        runtime=100,
        ratings=[
            Rating(name="themoviedb", value=6.8, votes=1718, max_value=10, is_default=False),
            Rating(name="imdb", value=7.0, votes=120000, max_value=10, is_default=True),
        ],
        genres=["Animation", "Science Fiction", "Thriller"],
        studios=["Warner Independent Pictures"],
        countries=["United States"],
        mpaa="R",
        certification="R",
        imdb_id="tt0405296",
        tmdb_id="3509",
        tvdb_id="4313",
        tags=["cyberpunk", "drugs"],
        actors=[
            Person(name="Keanu Reeves", role="Bob Arctor", tmdb_id="6384", thumb="https://example.com/keanu.jpg"),
            Person(name="Robert Downey Jr.", role="James Barris", tmdb_id="3223"),
        ],
        directors=[Person(name="Richard Linklater", person_type="Director", tmdb_id="564")],
        writers=[Person(name="Philip K. Dick", person_type="Writer", tmdb_id="584")],
        posters=["https://example.com/poster.jpg"],
        fanarts=["https://example.com/fanart1.jpg", "https://example.com/fanart2.jpg"],
        file_info=FileInfo(
            video=VideoStreamDetails(codec="h264", aspect="1.78", width=1920, height=1080, duration_seconds=6025),
            audio=[AudioStreamDetails(codec="AAC", language="eng", channels=2)],
        ),
    )

    xml_str = NFOBuilder.build_movie_nfo(movie)
    root = ET.fromstring(xml_str)

    assert root.tag == "movie"
    assert root.findtext("title") == "A Scanner Darkly"
    assert root.findtext("year") == "2006"
    assert root.findtext("runtime") == "100"
    assert root.findtext("id") == "tt0405296"
    assert root.findtext("tmdbid") == "3509"

    # Ratings
    ratings = root.findall("ratings/rating")
    assert len(ratings) == 2
    imdb_rating = next(r for r in ratings if r.get("name") == "imdb")
    assert imdb_rating.get("default") == "true"
    assert imdb_rating.findtext("value") == "7.0"

    # Actors
    actors = root.findall("actor")
    assert len(actors) == 2
    assert actors[0].findtext("name") == "Keanu Reeves"
    assert actors[0].findtext("role") == "Bob Arctor"
    assert actors[0].findtext("thumb") == "https://example.com/keanu.jpg"

    # Director & Writer
    assert root.findtext("director") == "Richard Linklater"
    assert root.findtext("writer") == "Philip K. Dick"

    # Tags
    tags = [elem.text for elem in root.findall("tag")]
    assert "cyberpunk" in tags
    assert "drugs" in tags

    # FileInfo
    assert root.findtext("fileinfo/streamdetails/video/codec") == "h264"
    assert root.findtext("fileinfo/streamdetails/video/width") == "1920"


def test_build_tvshow_nfo():
    show = TVShowMetadata(
        title="Blackadder",
        original_title="Blackadder",
        plot="Cunning plans and cutting comedy...",
        year=1983,
        status="Ended",
        tvdb_id="76736",
        imdb_id="tt0084988",
        tmdb_id="7246",
        genres=["Comedy"],
        studios=["BBC One"],
        countries=["United Kingdom"],
        tags=["sitcom", "historical comedy", "BBC One"],
        named_seasons={1: "The Black Adder", 2: "Blackadder II"},
        actors=[Person(name="Rowan Atkinson", role="Captain Edmund Blackadder", tvdb_id="274085")],
        posters=["https://example.com/show_poster.jpg"],
    )

    xml_str = NFOBuilder.build_tvshow_nfo(show)
    root = ET.fromstring(xml_str)

    assert root.tag == "tvshow"
    assert root.findtext("title") == "Blackadder"
    assert root.findtext("tvdbid") == "76736"
    assert root.findtext("namedseason[@number='1']") == "The Black Adder"
    assert root.findtext("actor/name") == "Rowan Atkinson"

    show_tags = [elem.text for elem in root.findall("tag")]
    assert "sitcom" in show_tags
    assert "historical comedy" in show_tags
    assert "BBC One" in show_tags


def test_build_season_nfo():
    season = SeasonMetadata(
        season_number=1,
        title="Season 1",
        plot="Set in 1485...",
        year=1983,
        premiered="1983-06-15",
        tags=["middle ages"],
    )
    xml_str = NFOBuilder.build_season_nfo(season)
    root = ET.fromstring(xml_str)

    assert root.tag == "season"
    assert root.findtext("seasonnumber") == "1"
    assert root.findtext("title") == "Season 1"
    assert root.findtext("sorttitle") == "0001"
    assert root.findtext("premiered") == "1983-06-15"
    assert [elem.text for elem in root.findall("tag")] == ["middle ages"]


def test_build_episode_nfo():
    ep = EpisodeMetadata(
        title="The Foretelling",
        season_number=1,
        episode_number=1,
        show_title="Blackadder",
        plot="After arriving late for the Battle of Bosworth Field...",
        aired="1983-06-15",
        year=1983,
        runtime=34,
        imdb_id="tt0526541",
        tvdb_id="213420",
        tags=["battle", "royalty"],
        actors=[Person(name="Rowan Atkinson", role="Edmund, Duke of Edinburgh")],
        directors=[Person(name="Martin Shardlow", person_type="Director")],
        writers=[Person(name="Rowan Atkinson", person_type="Writer"), Person(name="Richard Curtis", person_type="Writer")],
        thumbnail_url="https://example.com/s01e01.jpg",
    )
    xml_str = NFOBuilder.build_episode_nfo(ep)
    root = ET.fromstring(xml_str)

    assert root.tag == "episodedetails"
    assert root.findtext("title") == "The Foretelling"
    assert root.findtext("season") == "1"
    assert root.findtext("episode") == "1"
    assert root.findtext("imdbid") == "tt0526541"
    assert root.findtext("thumb") == "https://example.com/s01e01.jpg"
    assert root.findtext("director") == "Martin Shardlow"
    assert [elem.text for elem in root.findall("tag")] == ["battle", "royalty"]
