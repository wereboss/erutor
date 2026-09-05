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
