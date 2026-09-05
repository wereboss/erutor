"""Tests for tag extraction, normalization, and enrichment."""

from unittest.mock import MagicMock
import httpx
from erutor.tags import clean_tag, clean_wiki_category, deduplicate_tags, fetch_wikipedia_categories


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
