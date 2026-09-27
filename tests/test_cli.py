"""Tests for CLI commands and console progress reporting."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from erutor.cli import app
from erutor.models import MovieMetadata, TVShowMetadata, Rating, SeasonMetadata, EpisodeMetadata


def test_scan_movie_console_updates_with_tags(tmp_path: Path):
    # Setup test movie folder and video file
    movie_dir = tmp_path / "The Dark Knight (2008)"
    movie_dir.mkdir()
    video_file = movie_dir / "The.Dark.Knight.2008.mkv"
    video_file.touch()

    runner = CliRunner()

    mock_movie = MovieMetadata(
        title="The Dark Knight",
        year=2008,
        imdb_id="tt0468569",
        genres=["Action", "Crime"],
        tags=["action thriller", "superhero", "imax", "neo-noir", "2000s", "Feature Film"],
    )

    with patch("erutor.cli.ErutorManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr_cls.return_value = mock_mgr
        mock_mgr.search_movies.return_value = [MagicMock(id="tt0468569")]
        mock_mgr.get_movie.return_value = mock_movie
        mock_mgr.save_movie.return_value = {
            "nfo": movie_dir / "movie.nfo",
            "poster": movie_dir / "poster.jpg",
            "skipped": [],
        }

        result = runner.invoke(app, ["scan", str(tmp_path), "--no-images", "--force"])
        assert result.exit_code == 0
        assert "🎬 Movie: The Dark Knight (2008)" in result.stdout
        assert "6 Tags" in result.stdout
        assert "Updated: 1 NFO (movie.nfo), 6 Tags" in result.stdout
        assert "Total Metadata Tags Generated: 6" in result.stdout


def test_scan_tvshow_console_updates_with_tags(tmp_path: Path):
    show_dir = tmp_path / "Breaking Bad"
    show_dir.mkdir()
    season_dir = show_dir / "Season 1"
    season_dir.mkdir()
    ep_file = season_dir / "Breaking Bad - S01E01.mkv"
    ep_file.touch()

    runner = CliRunner()

    mock_show = TVShowMetadata(
        title="Breaking Bad",
        year=2008,
        imdb_id="tt0903747",
        genres=["Crime", "Drama"],
        tags=["organized crime", "illegal drug trade", "AMC", "Drama", "2000s"],
        seasons=[SeasonMetadata(season_number=1)],
        episodes=[EpisodeMetadata(title="Pilot", season_number=1, episode_number=1)],
    )

    with patch("erutor.cli.ErutorManager") as mock_mgr_cls:
        mock_mgr = MagicMock()
        mock_mgr_cls.return_value = mock_mgr
        mock_mgr.search_tv.return_value = [MagicMock(id="169")]
        mock_mgr.get_tvshow.return_value = mock_show
        mock_mgr.save_tvshow.return_value = {
            "nfo": [show_dir / "tvshow.nfo", season_dir / "season.nfo", season_dir / "ep.nfo"],
            "images": [],
            "skipped": [],
        }

        result = runner.invoke(app, ["scan", str(tmp_path), "--no-images", "--force"])
        assert result.exit_code == 0
        assert "📺 TV Series: Breaking Bad (2008)" in result.stdout
        assert "5 Tags" in result.stdout
        assert "Updated: 3 NFOs, 5 Tags" in result.stdout
        assert "Total Metadata Tags Generated: 5" in result.stdout
