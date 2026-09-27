"""Tag extraction, normalization, and enrichment utilities for media metadata."""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional

import httpx

# Common media stop words that are too generic as standalone tags
GENERIC_STOP_WORDS = {
    "film",
    "films",
    "movie",
    "movies",
    "tv",
    "television",
    "series",
    "show",
    "shows",
    "video",
    "videos",
    "media",
    "feature",
    "motion picture",
    "motion pictures",
}

# Accepted short tags (<= 2 chars)
ACCEPTED_SHORT_TAGS = {"ai", "ip", "vr", "tv", "4k", "3d", "hd"}


def clean_tag(tag: Optional[str]) -> Optional[str]:
    """Normalize and validate a tag string."""
    if not tag:
        return None

    cleaned = tag.strip().strip("\"'").strip()
    # Remove HTML tags if present
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Remove leading 'the ' (e.g. 'the future' -> 'future')
    cleaned = re.sub(r"^the\s+", "", cleaned, flags=re.IGNORECASE).strip()

    if len(cleaned) <= 2 and cleaned.lower() not in ACCEPTED_SHORT_TAGS:
        return None

    if cleaned.lower() in GENERIC_STOP_WORDS:
        return None

    return cleaned


def clean_wiki_category(cat: str, media_title: Optional[str] = None) -> Optional[str]:
    """Extract a high-quality thematic tag from a Wikipedia category name."""
    cat = cat.removeprefix("Category:").strip()

    # Ignore administrative, maintenance, award, and credit categories
    ignore_patterns = [
        r"^All\b",
        r"^Articles\b",
        r"^CS1\b",
        r"^Use\b",
        r"^Webarchive\b",
        r"^Pages\b",
        r"^Template\b",
        r"^Short description\b",
        r".*Wikidata",
        r".*Wikipedia",
        r"^Commons\b",
        r"^\d{4} films?$",
        r"^\d{4}s? .* debuts$",
        r"^\d{4}s? .* endings$",
        r".*articles.*",
        r".*redirects.*",
        r".*template.*",
        r".*sources.*",
        r".*extension.*",
        r".*arguments.*",
        r"Films directed by",
        r"Films produced by",
        r"Films scored by",
        r"Films photographed by",
        r"Screenplays by",
        r"Television series created by",
        r"Television series by .* Pictures",
        r"Television series by .* Productions",
        r"Television series by .* Entertainment",
        r"^[0-9]{4} (American|British|English-language|Japanese) films$",
        r"English-language .* shows$",
        r"American television shows$",
        r"Official website",
        r"Rotten Tomatoes",
        r".*winner.*",
        r".*award.*",
        r".*golden globe.*",
        r".*bafta.*",
        r".*emmy.*",
        r".*oscar.*",
        r"peabody",
        r".*productions?$",
        r".*entertainment$",
        r".*companies$",
    ]
    for pat in ignore_patterns:
        if re.search(pat, cat, re.IGNORECASE):
            return None

    # Transform common Wikipedia category patterns
    # 1. "Films about <topic>" or "Television series about <topic>"
    m = re.match(
        r"(?:(?:Animated|Action|Comedy|Drama|Science fiction|Independent) )?(?:Films|Television series|Television shows|Works) about (.+)",
        cat,
        re.IGNORECASE,
    )
    if m:
        res = m.group(1).lower().strip()
        res = re.sub(r"^the\s+", "", res)
        return clean_tag(res)

    # 2. "Films based on <source>"
    m = re.match(
        r"(?:(?:Animated|Action|Comedy|Drama|Science fiction|Independent) )?(?:Films|Television series) based on (.+)",
        cat,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1).lower().strip()
        if "novel" in val or "book" in val:
            return "based on novel or book"
        if "comic" in val or "graphic novel" in val or "manga" in val:
            return "based on comic"
        if "play" in val or "theatre" in val:
            return "based on play"
        if "video game" in val or "game" in val:
            return "based on video game"
        return f"based on {val}"

    # 3. "Films set in <location>" or "Films shot in <location>"
    m = re.match(
        r"(?:(?:Animated|Action|Comedy|Drama|Science fiction|Independent) )?(?:Films|Television (?:shows|series)) (?:set|shot) in (.+)",
        cat,
        re.IGNORECASE,
    )
    if m:
        loc = m.group(1).strip()
        # Avoid pure years: "set in 2008"
        if re.match(r"^\d{4}$", loc):
            return None
        loc = re.sub(r"^the\s+", "", loc, flags=re.IGNORECASE)
        return clean_tag(loc.lower())

    # 4. Remove decade/nationality prefixes and media suffixes
    cleaned = re.sub(r"^\d{4}s?\s+", "", cat)
    cleaned = re.sub(
        r"^(American|British|English-language|French|German|Japanese|Canadian|Australian|Spanish|Italian|Korean|Chinese)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+(?:television series|television shows|films|film)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^the\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\(genre\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.lower().strip()

    # Filter out production company / studio tags
    if re.search(r"\b(?:productions?|entertainment|pictures|studios?)\b", cleaned, re.IGNORECASE):
        return None

    # Filter out TV channel and adaptation artifacts
    if re.search(r"\(.*(?:channel|network)\)|television dramas$|adapted into|cultural depictions", cleaned, re.IGNORECASE):
        return None

    if media_title:
        m_lower = media_title.lower().strip()
        m_no_the = re.sub(r"^the\s+", "", m_lower).strip()
        if cleaned == m_lower or cleaned == m_no_the:
            return None

    return clean_tag(cleaned)


def resolve_wikipedia_page_title(
    client: httpx.Client,
    title: str,
    year: Optional[int] = None,
    imdb_id: Optional[str] = None,
    tvdb_id: Optional[str] = None,
    media_type: str = "movie",
) -> Optional[str]:
    """Resolve the exact canonical Wikipedia article title via Wikidata statement or opensearch."""
    # 1. Direct resolution via Wikidata IMDb statement (P345)
    if imdb_id:
        m = re.search(r"(tt\d+)", imdb_id, re.IGNORECASE)
        if m:
            clean_imdb = m.group(1).lower()
            try:
                r = client.get(
                    "https://www.wikidata.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": f"haswbstatement:P345={clean_imdb}",
                        "format": "json",
                    },
                )
                if r.status_code == 200:
                    hits = r.json().get("query", {}).get("search", [])
                    if hits:
                        qid = hits[0].get("title")
                        ent_r = client.get(
                            "https://www.wikidata.org/w/api.php",
                            params={
                                "action": "wbgetentities",
                                "ids": qid,
                                "props": "sitelinks",
                                "sitefilter": "enwiki",
                                "format": "json",
                            },
                        )
                        if ent_r.status_code == 200:
                            sitelinks = ent_r.json().get("entities", {}).get(qid, {}).get("sitelinks", {})
                            if "enwiki" in sitelinks and sitelinks["enwiki"].get("title"):
                                return sitelinks["enwiki"]["title"]
            except Exception:
                pass

    # 2. Direct resolution via Wikidata TVDB statement (P4835)
    if tvdb_id:
        clean_tvdb = re.sub(r"\D", "", tvdb_id)
        if clean_tvdb:
            try:
                r = client.get(
                    "https://www.wikidata.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": f"haswbstatement:P4835={clean_tvdb}",
                        "format": "json",
                    },
                )
                if r.status_code == 200:
                    hits = r.json().get("query", {}).get("search", [])
                    if hits:
                        qid = hits[0].get("title")
                        ent_r = client.get(
                            "https://www.wikidata.org/w/api.php",
                            params={
                                "action": "wbgetentities",
                                "ids": qid,
                                "props": "sitelinks",
                                "sitefilter": "enwiki",
                                "format": "json",
                            },
                        )
                        if ent_r.status_code == 200:
                            sitelinks = ent_r.json().get("entities", {}).get(qid, {}).get("sitelinks", {})
                            if "enwiki" in sitelinks and sitelinks["enwiki"].get("title"):
                                return sitelinks["enwiki"]["title"]
            except Exception:
                pass

    # 3. Fallback to candidate opensearch terms
    search_terms: list[str] = []
    if media_type == "movie":
        if year:
            search_terms.append(f"{title} ({year} film)")
        search_terms.append(f"{title} (film)")
        if year:
            search_terms.append(f"{title} {year} film")
        search_terms.append(f"{title} film")
        search_terms.append(title)
    else:
        if year:
            search_terms.append(f"{title} ({year} TV series)")
        search_terms.append(f"{title} (TV series)")
        if year:
            search_terms.append(f"{title} {year} TV series")
        search_terms.append(f"{title} TV series")
        search_terms.append(f"{title} (series)")
        search_terms.append(f"{title} series")
        search_terms.append(title)

    for term in search_terms:
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(term)}&limit=3&format=json"
            r = client.get(search_url)
            if r.status_code == 200:
                candidates = r.json()[1]
                if candidates:
                    return candidates[0]
        except Exception:
            continue

    return None


def fetch_wikipedia_categories(
    client: httpx.Client,
    page_title: str,
    media_title: Optional[str] = None,
    max_categories: int = 25,
) -> list[str]:
    """Query Wikipedia categories for a page title and return cleaned tags."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "categories",
        "titles": page_title,
        "redirects": "1",
        "cllimit": "max",
        "format": "json",
    }
    try:
        resp = client.get(url, params=params)
        if resp.status_code != 200:
            return []
        pages = resp.json().get("query", {}).get("pages", {})
        tags: list[str] = []
        for p in pages.values():
            for c in p.get("categories", []):
                cleaned = clean_wiki_category(c.get("title", ""), media_title=media_title)
                if cleaned and cleaned not in tags:
                    tags.append(cleaned)
                    if len(tags) >= max_categories:
                        break
            if len(tags) >= max_categories:
                break
        return tags
    except Exception:
        return []


def deduplicate_tags(tags: list[str]) -> list[str]:
    """Deduplicate tags preserving order (case-insensitively)."""
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        cleaned = clean_tag(t)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
