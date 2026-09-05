"""Unit tests for TitleParser."""

from erutor.parser import TitleParser


def test_parse_movie_scene_release():
    parsed = TitleParser.parse("A.Scanner.Darkly.2006.1080p.BluRay.x264.YIFY.mp4")
    assert parsed.media_type == "movie"
    assert parsed.title == "A Scanner Darkly"
    assert parsed.year == 2006
    assert parsed.resolution == "1080p"
    assert parsed.source == "BluRay"
    assert parsed.video_codec == "x264"
    assert parsed.release_group == "YIFY"


def test_parse_tv_episode_with_parentheses_and_tags():
    parsed = TitleParser.parse("Blackadder (1983) - S01E01 - The Foretelling (576p DVD x265 Panda).mp4")
    assert parsed.media_type == "tv"
    assert parsed.title == "Blackadder"
    assert parsed.year == 1983
    assert parsed.season == 1
    assert parsed.episode == 1
    assert parsed.episode_title == "The Foretelling"
    assert parsed.resolution == "576p"
    assert parsed.source == "DVD"
    assert parsed.video_codec == "x265"
    assert parsed.release_group == "Panda"


def test_parse_tv_multi_episode():
    parsed = TitleParser.parse("The.Office.US.S03E01-E02.1080p.WEB-DL.mkv")
    assert parsed.media_type == "tv"
    assert parsed.title == "The Office US"
    assert parsed.season == 3
    assert parsed.episode == 1
    assert parsed.episode_end == 2
    assert parsed.resolution == "1080p"
    assert parsed.source == "WEB-DL"


def test_parse_tv_standard_1x01():
    parsed = TitleParser.parse("Doctor.Who.2005.1x01.Rose.720p.mkv")
    assert parsed.media_type == "tv"
    assert parsed.title == "Doctor Who"
    assert parsed.year == 2005
    assert parsed.season == 1
    assert parsed.episode == 1
    assert parsed.episode_title == "Rose"
    assert parsed.resolution == "720p"


def test_parse_season_pack_folder():
    parsed = TitleParser.parse("Breaking.Bad.Season.1.1080p")
    assert parsed.media_type == "tv"
    assert parsed.title == "Breaking Bad"
    assert parsed.season == 1
    assert parsed.resolution == "1080p"


def test_parse_movie_with_dash_release_group():
    parsed = TitleParser.parse("Inception.2010.1080p.BluRay.x264-SPARKS.mkv")
    assert parsed.media_type == "movie"
    assert parsed.title == "Inception"
    assert parsed.year == 2010
    assert parsed.resolution == "1080p"
    assert parsed.source == "BluRay"
    assert parsed.video_codec == "x264"
    assert parsed.release_group == "SPARKS"


def test_parse_4k_uhd_hevc():
    parsed = TitleParser.parse("The.Matrix.1999.2160p.UHD.HDR.HEVC.Atmos-SWTYBLZ.mkv")
    assert parsed.media_type == "movie"
    assert parsed.title == "The Matrix"
    assert parsed.year == 1999
    assert parsed.resolution == "2160p"
    assert parsed.video_codec == "x265"
    assert parsed.release_group == "SWTYBLZ"
