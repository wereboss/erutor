"""Tests for tag extraction, normalization, and enrichment."""

from unittest.mock import MagicMock
import httpx
from erutor.tags import (
    clean_tag,
    clean_wiki_category,
    deduplicate_tags,
    fetch_wikipedia_categories,
    resolve_wikipedia_page_title,
)


def test_clean_tag():
    assert clean_tag("  the future  ") == "future"
    assert clean_tag("The Matrix") == "Matrix"
    assert clean_tag("cyberpunk") == "cyberpunk"
    assert clean_tag("a") is None
    assert clean_tag("AI") == "AI"
    assert clean_tag("4k") == "4k"
    assert clean_tag("movie") is None
    assert clean_tag("television") is None
    assert clean_tag("film") is None
    assert clean_tag("<tag>dystopia</tag>") == "dystopia"


def test_clean_wiki_category():
    # Administrative & maintenance ignored
    assert clean_wiki_category("Category:All Wikipedia articles written in American English") is None
    assert clean_wiki_category("Category:Articles with short description") is None
    assert clean_wiki_category("Category:CS1 maint: unfit URL") is None
    assert clean_wiki_category("Category:Use mdy dates from April 2022") is None
    assert clean_wiki_category("Category:2006 films") is None
    assert clean_wiki_category("Category:Films directed by Richard Linklater") is None
    assert clean_wiki_category("Category:BAFTA winners (television series)") is None
    assert clean_wiki_category("Category:Primetime Emmy Award winners") is None

    # Thematic and content categories extracted
    assert clean_wiki_category("Category:2000s dystopian films") == "dystopian"
    assert clean_wiki_category("Category:Animated films set in California") == "california"
    assert clean_wiki_category("Category:Animated films set in the future") == "future"
    assert clean_wiki_category("Category:Films about mass surveillance") == "mass surveillance"
    assert clean_wiki_category("Category:Films about substance abuse") == "substance abuse"
    assert clean_wiki_category("Category:Films based on science fiction novels") == "based on novel or book"
    assert clean_wiki_category("Category:Films based on Marvel Comics") == "based on comic"
    assert clean_wiki_category("Category:Films based on video games") == "based on video game"
    assert clean_wiki_category("Category:Rotoscoped films") == "rotoscoped"
    assert clean_wiki_category("Category:Television series about organized crime") == "organized crime"
    assert clean_wiki_category("Category:Television series about the illegal drug trade") == "illegal drug trade"
    assert clean_wiki_category("Category:Television shows set in New Mexico") == "new mexico"
    assert clean_wiki_category("Category:2000s American crime drama television series") == "crime drama"

    # Self-referential match
    assert clean_wiki_category("Category:Breaking Bad", media_title="Breaking Bad") is None
    assert clean_wiki_category("Category:The Godfather", media_title="The Godfather") is None
    assert clean_wiki_category("Category:Godfather", media_title="The Godfather") is None


def test_deduplicate_tags():
    raw = ["Cyberpunk", "future", "CYBERPUNK", "Future", "dystopia", "  the future  ", ""]
    deduped = deduplicate_tags(raw)
    assert deduped == ["Cyberpunk", "future", "dystopia"]


def test_fetch_wikipedia_categories():
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "categories": [
                        {"title": "Category:2000s dystopian films"},
                        {"title": "Category:All Wikipedia articles written in American English"},
                        {"title": "Category:Films about mass surveillance"},
                        {"title": "Category:Films directed by Richard Linklater"},
                    ]
                }
            }
        }
    }
    mock_client.get.return_value = mock_resp

    tags = fetch_wikipedia_categories(mock_client, "A Scanner Darkly (film)", media_title="A Scanner Darkly")
    assert "dystopian" in tags
    assert "mass surveillance" in tags
    assert "All Wikipedia articles written in American English" not in tags
    assert not any("Linklater" in t for t in tags)


def test_resolve_wikipedia_page_title_wikidata_imdb():
    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        params = kwargs.get("params", {})
        if "haswbstatement:P345" in params.get("srsearch", ""):
            resp.json.return_value = {"query": {"search": [{"title": "Q163872"}]}}
        elif params.get("action") == "wbgetentities" and params.get("ids") == "Q163872":
            resp.json.return_value = {
                "entities": {"Q163872": {"sitelinks": {"enwiki": {"title": "The Dark Knight"}}}}
            }
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    title = resolve_wikipedia_page_title(mock_client, "The Dark Knight", imdb_id="tt0468569")
    assert title == "The Dark Knight"


def test_resolve_wikipedia_page_title_wikidata_tvdb():
    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        params = kwargs.get("params", {})
        if "haswbstatement:P4835" in params.get("srsearch", ""):
            resp.json.return_value = {"query": {"search": [{"title": "Q117706339"}]}}
        elif params.get("action") == "wbgetentities" and params.get("ids") == "Q117706339":
            resp.json.return_value = {
                "entities": {"Q117706339": {"sitelinks": {"enwiki": {"title": "A Knight of the Seven Kingdoms (TV series)"}}}}
            }
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    title = resolve_wikipedia_page_title(mock_client, "A Knight of the Seven Kingdoms", tvdb_id="433631", media_type="tv")
    assert title == "A Knight of the Seven Kingdoms (TV series)"


def test_resolve_wikipedia_page_title_opensearch_fallback():
    mock_client = MagicMock(spec=httpx.Client)

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "opensearch" in url and "1972" in url:
            resp.json.return_value = ["The Godfather (1972 film)", ["The Godfather (1972 film)"]]
        else:
            resp.json.return_value = {}
        return resp

    mock_client.get.side_effect = mock_get

    title = resolve_wikipedia_page_title(mock_client, "The Godfather", year=1972, media_type="movie")
    assert title == "The Godfather (1972 film)"
