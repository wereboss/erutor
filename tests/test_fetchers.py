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


def test_imdb_free_get_movie_tags():
    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "suggestion" in url:
            resp.json.return_value = {
                "d": [{"id": "tt0405296", "l": "A Scanner Darkly", "y": 2006, "s": "Keanu Reeves"}]
            }
        elif "opensearch" in url:
            resp.json.return_value = ["A Scanner Darkly", ["A Scanner Darkly (film)"]]
        elif "api/rest_v1/page/summary" in url:
            resp.json.return_value = {
                "extract": "A Scanner Darkly is an animated science fiction thriller directed by Richard Linklater.",
            }
        elif "categories" in kwargs.get("params", {}).get("prop", ""):
            resp.json.return_value = {
                "query": {
                    "pages": {
                        "1": {
                            "categories": [
                                {"title": "Category:2000s dystopian films"},
                                {"title": "Category:Animated films set in California"},
                                {"title": "Category:Films about mass surveillance"},
                            ]
                        }
                    }
                }
            }
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    fetcher = FreeMovieFetcher(client=mock_client)
    movie = fetcher.get_movie("tt0405296")
    assert movie is not None
    assert "dystopian" in movie.tags
    assert "california" in movie.tags
    assert "mass surveillance" in movie.tags


def test_tvmaze_get_tvshow_tags():
    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "api.tvmaze.com/shows" in url:
            resp.json.return_value = {
                "id": 169,
                "name": "Breaking Bad",
                "type": "Scripted",
                "language": "English",
                "genres": ["Drama", "Crime", "Thriller"],
                "network": {"name": "AMC"},
                "_embedded": {
                    "seasons": [{"number": 1, "name": "Season 1"}],
                    "episodes": [{"number": 1, "season": 1, "name": "Pilot"}],
                    "cast": [],
                },
            }
        elif "opensearch" in url:
            resp.json.return_value = ["Breaking Bad", ["Breaking Bad (TV series)"]]
        elif "categories" in kwargs.get("params", {}).get("prop", ""):
            resp.json.return_value = {
                "query": {
                    "pages": {
                        "1": {
                            "categories": [
                                {"title": "Category:Television series about organized crime"},
                                {"title": "Category:Television series about the illegal drug trade"},
                            ]
                        }
                    }
                }
            }
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    fetcher = TVMazeFetcher(client=mock_client)
    show = fetcher.get_tvshow("169")
    assert show is not None
    assert "Scripted" in show.tags
    assert "AMC" in show.tags
    assert "organized crime" in show.tags
    assert "illegal drug trade" in show.tags
    assert len(show.episodes[0].tags) > 0


def test_tmdb_tags():
    from erutor.fetchers.tmdb import TMDBFetcher

    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "/movie/" in url:
            resp.json.return_value = {
                "id": 3509,
                "title": "A Scanner Darkly",
                "release_date": "2006-07-07",
                "keywords": {
                    "keywords": [
                        {"id": 1, "name": "cyberpunk"},
                        {"id": 2, "name": "future"},
                        {"id": 3, "name": "drugs"},
                    ]
                },
            }
        elif "/tv/" in url:
            resp.json.return_value = {
                "id": 1396,
                "name": "Breaking Bad",
                "first_air_date": "2008-01-20",
                "keywords": {
                    "results": [
                        {"id": 1, "name": "drug dealer"},
                        {"id": 2, "name": "cancer"},
                    ]
                },
            }
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    fetcher = TMDBFetcher(api_key="test_key", client=mock_client)
    movie = fetcher.get_movie("3509")
    assert movie is not None
    assert movie.tags == ["cyberpunk", "future", "drugs"]

    show = fetcher.get_tvshow("1396")
    assert show is not None
    assert show.tags == ["drug dealer", "cancer"]

