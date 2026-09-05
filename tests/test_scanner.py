"""Unit tests for DirectoryScanner."""

from pathlib import Path
from erutor.scanner import DirectoryScanner


def test_directory_scanner_movies_and_tv(tmp_path: Path):
    # Setup mock library
    movie_dir = tmp_path / "A Scanner Darkly (2006)"
    movie_dir.mkdir()
    movie_file = movie_dir / "A.Scanner.Darkly.2006.1080p.BluRay.x264.YIFY.mp4"
    movie_file.write_text("dummy video")

    # Add existing poster to test conflict detection
    poster_file = movie_dir / "poster.jpg"
    poster_file.write_text("dummy poster")

    # Setup TV show
    tv_dir = tmp_path / "Blackadder (1983)"
    s1_dir = tv_dir / "Season 1"
    s1_dir.mkdir(parents=True)
    ep_file = s1_dir / "Blackadder - S01E01 - The Foretelling.mp4"
    ep_file.write_text("dummy episode")

    # Scan
    items = DirectoryScanner.scan(tmp_path)
    assert len(items) == 2

    # Check movie
    movie_item = next(i for i in items if i.media_type == "movie")
    assert movie_item.title == "A Scanner Darkly"
    assert movie_item.year == 2006
    assert movie_item.has_poster is True
    assert movie_item.has_nfo is False
    assert "poster" in movie_item.existing_metadata_desc

    # Check TV show
    tv_item = next(i for i in items if i.media_type == "tv")
    assert tv_item.title == "Blackadder"
    assert tv_item.year == 1983
    assert 1 in tv_item.seasons
    assert len(tv_item.seasons[1]) == 1
    assert tv_item.seasons[1][0].season_number == 1
    assert tv_item.seasons[1][0].episode_number == 1
