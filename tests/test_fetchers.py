"""Tests for metadata fetchers."""

from unittest.mock import MagicMock
import httpx
from erutor.config import Config
from erutor.fetchers.tvmaze import TVMazeFetcher
from erutor.fetchers.imdb_free import FreeMovieFetcher


def test_tvmaze_search():
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {
            "show": {
                "id": 1072,
                "name": "Blackadder",
                "premiered": "1983-06-15",
                "summary": "<p>Comedy series.</p>",
                "image": {"original": "https://example.com/poster.jpg"},
            }
        }
    ]
    mock_client.get.return_value = mock_resp

    fetcher = TVMazeFetcher(client=mock_client)
    results = fetcher.search_tv("Blackadder", year=1983)
    assert len(results) == 1
    assert results[0].title == "Blackadder"
    assert results[0].year == 1983
    assert results[0].overview == "Comedy series."
    assert results[0].poster_url == "https://example.com/poster.jpg"


def test_tvmaze_year_based_season_remapping():
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": 555,
        "name": "Columbo",
        "premiered": "1968-02-20",
        "status": "Ended",
        "_embedded": {
            "seasons": [
                {"number": 1968, "name": "", "premiereDate": "1968-02-20"},
                {"number": 1971, "name": "", "premiereDate": "1971-03-01"},
                {"number": 1972, "name": "", "premiereDate": "1972-09-17"},
            ],
            "episodes": [
                {"name": "Prescription: Murder", "season": 1968, "number": 1, "airdate": "1968-02-20"},
                {"name": "Ransom for a Dead Man", "season": 1971, "number": 1, "airdate": "1971-03-01"},
                {"name": "Murder by the Book", "season": 1971, "number": 2, "airdate": "1971-09-15"},
            ],
            "cast": [],
        },
    }
    mock_client.get.return_value = mock_resp

    fetcher = TVMazeFetcher(client=mock_client)
    show = fetcher.get_tvshow("555")
    assert show is not None

    # Check seasons are mapped to 1, 2, 3
    assert len(show.seasons) == 3
    assert show.seasons[0].season_number == 1
    assert show.seasons[0].title == "Season 1"
    assert show.seasons[0].year == 1968

    assert show.seasons[1].season_number == 2
    assert show.seasons[1].title == "Season 2"
    assert show.seasons[1].year == 1971

    assert show.seasons[2].season_number == 3
    assert show.seasons[2].title == "Season 3"
    assert show.seasons[2].year == 1972

    # Check episodes are mapped to 1, 2
    assert len(show.episodes) == 3
    assert show.episodes[0].season_number == 1
    assert show.episodes[0].episode_number == 1

    assert show.episodes[1].season_number == 2
    assert show.episodes[1].episode_number == 1

    assert show.episodes[2].season_number == 2
    assert show.episodes[2].episode_number == 2


def test_imdb_free_search():
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "d": [
            {
                "id": "tt0405296",
                "l": "A Scanner Darkly",
                "y": 2006,
                "q": "feature",
                "qid": "movie",
                "s": "Keanu Reeves, Winona Ryder",
                "i": {"imageUrl": "https://example.com/darkly.jpg"},
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    fetcher = FreeMovieFetcher(client=mock_client)
    results = fetcher.search_movie("A Scanner Darkly", year=2006)
    assert len(results) == 1
    assert results[0].id == "tt0405296"
    assert results[0].title == "A Scanner Darkly"
    assert results[0].year == 2006
    assert "Keanu Reeves" in (results[0].overview or "")


def test_config_defaults():
    cfg = Config()
    assert cfg.movie_nfo_name == "movie.nfo"
    assert cfg.tvshow_nfo_name == "tvshow.nfo"
    assert cfg.poster_name == "poster.jpg"
    assert cfg.fanart_name == "fanart.jpg"
    assert cfg.download_images is True
