"""Advanced title and media information parser from file and folder names."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Common video file extensions
VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".m4v",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".ts",
    ".iso",
    ".nfo",
}

# Resolutions
RESOLUTIONS = [
    (r"\b2160p\b|\b4k\b|\buhd\b", "2160p"),
    (r"\b1080p\b|\bfullhd\b", "1080p"),
    (r"\b1080i\b", "1080i"),
    (r"\b720p\b|\bhd\b", "720p"),
    (r"\b576p\b|\b576i\b", "576p"),
    (r"\b480p\b|\b480i\b|\bsd\b", "480p"),
]

# Media Sources
SOURCES = [
    (r"\bbluray\b|\bblu-ray\b|\bbdrip\b|\bbrrip\b", "BluRay"),
    (r"\bremux\b", "REMUX"),
    (r"\bweb-dl\b|\bwebdl\b|\bweb-rip\b|\bwebrip\b|\bweb\b", "WEB-DL"),
    (r"\bhdtv\b|\bpdtv\b|\bdsr\b", "HDTV"),
    (r"\bdvdrip\b|\bdvd\b|\bdvd-r\b", "DVD"),
    (r"\bcam\b|\bts\b|\btelesync\b", "CAM"),
]

# Video Codecs
VIDEO_CODECS = [
    (r"\bx265\b|\bh265\b|\bh\.265\b|\bhevc\b", "x265"),
    (r"\bx264\b|\bh264\b|\bh\.264\b|\bavc\b", "x264"),
    (r"\bxvid\b|\bdivx\b", "XviD"),
    (r"\bav1\b", "AV1"),
    (r"\bmpeg2\b|\bvc1\b", "MPEG2"),
]

# Audio Codecs / Formats
AUDIO_CODECS = [
    (r"\batmos\b", "Dolby Atmos"),
    (r"\bddp5\.1\b|\bdd\+5\.1\b|\beac3\b", "DDP 5.1"),
    (r"\bdd5\.1\b|\bac3\b|\bac-3\b", "DD 5.1"),
    (r"\bdts-hd[\s._-]?ma\b", "DTS-HD MA"),
    (r"\bdts\b", "DTS"),
    (r"\btruehd\b", "TrueHD"),
    (r"\baac(?:\d(?:\.1)?)?\b", "AAC"),
    (r"\bflac\b", "FLAC"),
    (r"\bmp3\b", "MP3"),
]

# Scene and edition noise tokens to strip
SCENE_NOISE = [
    r"\bproper\b",
    r"\brepack\b",
    r"\brerip\b",
    r"\bremastered\b",
    r"\bextended(?:\s+cut|\s+edition)?\b",
    r"\bunrated\b",
    r"\bdirectors(?:\s+cut)?\b",
    r"\btheatrical(?:\s+cut)?\b",
    r"\bcriterion\b",
    r"\bimax\b",
    r"\binternal\b",
    r"\blimited\b",
    r"\bfull(?:\s+screen)?\b",
    r"\bws\b|\bwidescreen\b",
    r"\bdual[\s._-]?audio\b",
    r"\bmulti(?:[\s._-]?subs?)?\b",
    r"\bcomplete\b",
    r"\b10bit\b|\b8bit\b",
    r"\bhdr(?:10(?:\+)?)?\b|\bdolby[\s._-]?vision\b|\bdv\b",
]

# Known release groups
COMMON_GROUPS = [
    "yify",
    "yts",
    "yts.mx",
    "yts.am",
    "rarbg",
    "sparks",
    "geckos",
    "amiable",
    "rovers",
    "fgt",
    "galaxyrg",
    "panda",
    "ettv",
    "eztv",
    "dimension",
    "killers",
    "fleet",
    "cmrg",
]


@dataclass
class ParsedMedia:
    raw_name: str
    title: str
    year: Optional[int] = None
    media_type: str = "unknown"  # "movie", "tv", or "unknown"
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None
    episode_title: Optional[str] = None
    resolution: Optional[str] = None
    source: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    release_group: Optional[str] = None

    def clean_query(self) -> str:
        """Returns clean title suitable for search queries."""
        return self.title


def _clean_separators(text: str) -> str:
    """Replace dots, underscores, and excessive spaces with a single space."""
    # Replace dots and underscores with space
    cleaned = re.sub(r"[._]+", " ", text)
    # Remove enclosing parentheses/brackets if around the whole string
    cleaned = re.sub(r"^[\[(]+|[\])]+$", "", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class TitleParser:
    """Intelligent title and metadata parser for filenames and directory names."""

    @classmethod
    def parse(cls, input_path_or_name: str | Path) -> ParsedMedia:
        raw = str(input_path_or_name)
        path = Path(raw)
        filename = path.name

        # Strip video extension if present
        ext = path.suffix.lower()
        base_name = path.stem if ext in VIDEO_EXTENSIONS else filename

        working_name = base_name

        # 1. Extract Release Group (usually at the very end after a dash)
        release_group = None
        group_match = re.search(r"-([A-Za-z0-9_]+)$", working_name)
        if group_match:
            candidate = group_match.group(1).lower()
            # Verify candidate isn't a codec/source or common keyword
            not_group = any(re.search(p, candidate, re.IGNORECASE) for p, _ in VIDEO_CODECS + SOURCES + RESOLUTIONS + AUDIO_CODECS)
            if not not_group and candidate not in ("dl", "rip", "web", "hd"):
                release_group = group_match.group(1)
                working_name = working_name[: group_match.start()]
        if not release_group:
            for g in COMMON_GROUPS:
                m = re.search(rf"\b({re.escape(g)})\b", working_name, re.IGNORECASE)
                if m:
                    release_group = m.group(1)
                    break

        # 2. Extract Technical Tags (Resolution, Source, Codecs)
        resolution = None
        for pattern, res_name in RESOLUTIONS:
            if re.search(pattern, working_name, re.IGNORECASE):
                resolution = res_name
                break

        source = None
        for pattern, src_name in SOURCES:
            if re.search(pattern, working_name, re.IGNORECASE):
                source = src_name
                break

        video_codec = None
        for pattern, codec_name in VIDEO_CODECS:
            if re.search(pattern, working_name, re.IGNORECASE):
                video_codec = codec_name
                break

        audio_codec = None
        for pattern, acodec_name in AUDIO_CODECS:
            if re.search(pattern, working_name, re.IGNORECASE):
                audio_codec = acodec_name
                break

        # 3. Check for TV Show Patterns (S01E02, 1x02, etc.)
        # Pattern A: S01E02 or S01E02-E03 or S01E02E03
        tv_match_a = re.search(
            r"[\s._\-\[]+[sS](\d{1,2})[\s._-]*[eE](\d{1,3})(?:[\s._-]*(?:-|[eE])[\s._-]*(\d{1,3}))?[\s._\-\]]*",
            working_name,
        )
        # Pattern B: 1x02 or 01x02
        tv_match_b = re.search(r"[\s._\-\[]+(\d{1,2})x(\d{1,3})[\s._\-\]]*", working_name)
        # Pattern C: Season 1 Episode 2
        tv_match_c = re.search(
            r"[\s._\-\[]+[sS]eason[\s._-]*(\d{1,2})[\s._-]+[eE]pisode[\s._-]*(\d{1,3})[\s._\-\]]*",
            working_name,
            re.IGNORECASE,
        )

        season: Optional[int] = None
        episode: Optional[int] = None
        episode_end: Optional[int] = None
        is_tv = False
        split_pos = -1

        if tv_match_a:
            is_tv = True
            season = int(tv_match_a.group(1))
            episode = int(tv_match_a.group(2))
            if tv_match_a.group(3):
                episode_end = int(tv_match_a.group(3))
            split_pos = tv_match_a.start()
            remainder = working_name[tv_match_a.end() :]
        elif tv_match_b:
            is_tv = True
            season = int(tv_match_b.group(1))
            episode = int(tv_match_b.group(2))
            split_pos = tv_match_b.start()
            remainder = working_name[tv_match_b.end() :]
        elif tv_match_c:
            is_tv = True
            season = int(tv_match_c.group(1))
            episode = int(tv_match_c.group(2))
            split_pos = tv_match_c.start()
            remainder = working_name[tv_match_c.end() :]
        else:
            remainder = ""

        # Check for year (e.g. (1983) or .2006.)
        year: Optional[int] = None
        year_match = re.search(r"(?:\(|\.|\[|\s|_)(19\d{2}|20\d{2})(?:\)|\.|\]|\s|_|$)", working_name)

        title = ""
        episode_title: Optional[str] = None

        if is_tv:
            raw_show_part = working_name[:split_pos]
            # Check if show title itself has year in it: e.g. "Blackadder (1983)"
            show_year_match = re.search(r"(?:\(|\.|\[|\s|_)(19\d{2}|20\d{2})(?:\)|\.|\]|\s|_|$)", raw_show_part)
            if show_year_match:
                year = int(show_year_match.group(1))
                # Title is before year
                raw_show_part = raw_show_part[: show_year_match.start()]

            title = _clean_separators(raw_show_part)

            # Parse episode title from remainder if present
            if remainder:
                # Remove quality and noise tags from remainder
                ep_remainder = remainder
                cut_idx = len(ep_remainder)
                for pattern, _ in RESOLUTIONS + SOURCES + VIDEO_CODECS + AUDIO_CODECS:
                    m = re.search(pattern, ep_remainder, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()
                for noise in SCENE_NOISE:
                    m = re.search(noise, ep_remainder, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()
                if release_group:
                    m = re.search(rf"\b{re.escape(release_group)}\b", ep_remainder, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()

                candidate_ep_title = ep_remainder[:cut_idx]
                clean_ep = _clean_separators(candidate_ep_title)
                # Strip leading/trailing hyphen, parentheses, brackets
                clean_ep = re.sub(r"^[\s\-–—([\]]+|[\s\-–—([\]]+$", "", clean_ep).strip()
                if clean_ep:
                    episode_title = clean_ep

        else:
            # Check if it's a TV season pack folder (e.g. "Breaking Bad Season 1" or "Chernobyl S01")
            season_pack_match = re.search(r"[\s._\-\[]+(?:[sS]eason[\s._-]*(\d{1,2})|[sS](\d{1,2}))[\s._\-\]]*", working_name, re.IGNORECASE)
            if season_pack_match:
                is_tv = True
                season = int(season_pack_match.group(1) or season_pack_match.group(2))
                raw_show = working_name[: season_pack_match.start()]
                if year_match and year_match.start() < season_pack_match.start():
                    year = int(year_match.group(1))
                    raw_show = raw_show[: year_match.start()]
                title = _clean_separators(raw_show)

            elif year_match:
                year = int(year_match.group(1))
                # Movie title is everything before the year
                raw_title_part = working_name[: year_match.start()]
                title = _clean_separators(raw_title_part)
            else:
                # No year or TV pattern: cut at first technical tag / noise
                cut_idx = len(working_name)
                for pattern, _ in RESOLUTIONS + SOURCES + VIDEO_CODECS + AUDIO_CODECS:
                    m = re.search(pattern, working_name, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()
                for noise in SCENE_NOISE:
                    m = re.search(noise, working_name, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()
                if release_group:
                    m = re.search(rf"\b{re.escape(release_group)}\b", working_name, re.IGNORECASE)
                    if m and m.start() < cut_idx:
                        cut_idx = m.start()

                title = _clean_separators(working_name[:cut_idx])

        # Default media type
        if is_tv:
            media_type = "tv"
        elif year is not None or resolution is not None or source is not None:
            media_type = "movie"
        else:
            media_type = "unknown"

        return ParsedMedia(
            raw_name=filename,
            title=title,
            year=year,
            media_type=media_type,
            season=season,
            episode=episode,
            episode_end=episode_end,
            episode_title=episode_title,
            resolution=resolution,
            source=source,
            video_codec=video_codec,
            audio_codec=audio_codec,
            release_group=release_group,
        )
