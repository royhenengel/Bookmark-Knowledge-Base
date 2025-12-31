"""
Unit tests for video-enricher Cloud Function.

Tests pure functions that don't require external API calls.
"""

import pytest


class TestIsSpotifyPodcast:
    """Tests for is_spotify_podcast()"""

    def test_spotify_episode_url(self, is_spotify_podcast):
        url = "https://open.spotify.com/episode/abc123XYZ"
        assert is_spotify_podcast(url) is True

    def test_spotify_episode_uppercase(self, is_spotify_podcast):
        url = "https://OPEN.SPOTIFY.COM/EPISODE/ABC123"
        assert is_spotify_podcast(url) is True

    def test_spotify_episode_mixed_case(self, is_spotify_podcast):
        url = "https://Open.Spotify.Com/Episode/abc123"
        assert is_spotify_podcast(url) is True

    def test_spotify_album_url(self, is_spotify_podcast):
        url = "https://open.spotify.com/album/abc123"
        assert is_spotify_podcast(url) is False

    def test_spotify_track_url(self, is_spotify_podcast):
        url = "https://open.spotify.com/track/abc123"
        assert is_spotify_podcast(url) is False

    def test_spotify_playlist_url(self, is_spotify_podcast):
        url = "https://open.spotify.com/playlist/abc123"
        assert is_spotify_podcast(url) is False

    def test_youtube_url(self, is_spotify_podcast):
        url = "https://youtube.com/watch?v=abc123"
        assert is_spotify_podcast(url) is False

    def test_tiktok_url(self, is_spotify_podcast):
        url = "https://www.tiktok.com/@user/video/123"
        assert is_spotify_podcast(url) is False

    def test_empty_url(self, is_spotify_podcast):
        assert is_spotify_podcast("") is False

    def test_spotify_show_url(self, is_spotify_podcast):
        url = "https://open.spotify.com/show/abc123"
        assert is_spotify_podcast(url) is False


class TestGenerateSmartFilename:
    """Tests for generate_smart_filename()"""

    def test_basic_filename(self, generate_smart_filename):
        result = generate_smart_filename("My Video Title", "some_user", "mp4")
        assert result == "My Video Title - Some User.mp4"

    def test_special_characters_removed(self, generate_smart_filename):
        """Common punctuation is preserved, but @#$ etc are removed."""
        result = generate_smart_filename("Title: With @Special# Chars!", "user", "mp4")
        # New behavior: keeps common punctuation like : and !
        # Removes @ and # symbols
        assert "Title:" in result
        assert "Chars!" in result
        assert "@" not in result
        assert "#" not in result

    def test_underscores_in_uploader_converted(self, generate_smart_filename):
        result = generate_smart_filename("Video", "john_doe_123", "mp4")
        assert "John Doe 123" in result

    def test_default_extension(self, generate_smart_filename):
        result = generate_smart_filename("Title", "user")
        assert result.endswith(".mp4")

    def test_custom_extension_webm(self, generate_smart_filename):
        result = generate_smart_filename("Title", "user", "webm")
        assert result.endswith(".webm")

    def test_custom_extension_mkv(self, generate_smart_filename):
        result = generate_smart_filename("Title", "user", "mkv")
        assert result.endswith(".mkv")

    def test_long_title_truncated(self, generate_smart_filename):
        long_title = "A" * 150  # 150 characters
        result = generate_smart_filename(long_title, "user", "mp4")
        # Title is truncated to 80 chars, then " - User.mp4" is added
        assert len(result) <= 100  # 80 + " - User" + ".mp4"

    def test_title_with_emojis_filtered(self, generate_smart_filename):
        # Emojis are not alphanumeric so they get removed
        result = generate_smart_filename("Cool Video 🔥✨", "creator", "mp4")
        assert "🔥" not in result
        assert "✨" not in result
        assert "Cool Video" in result

    def test_multiple_spaces_normalized(self, generate_smart_filename):
        result = generate_smart_filename("Title   with    spaces", "user", "mp4")
        assert "   " not in result  # Multiple spaces should be normalized

    def test_uploader_capitalized(self, generate_smart_filename):
        result = generate_smart_filename("Video", "lowercase_user", "mp4")
        assert "Lowercase User" in result

    def test_numbers_preserved(self, generate_smart_filename):
        result = generate_smart_filename("Part 1 of 10", "user2023", "mp4")
        assert "Part 1 of 10" in result
        assert "User2023" in result

    def test_empty_title(self, generate_smart_filename):
        result = generate_smart_filename("", "user", "mp4")
        # Should handle empty title gracefully
        assert result.endswith(".mp4")
        assert "User" in result

    def test_empty_uploader(self, generate_smart_filename):
        result = generate_smart_filename("Title", "", "mp4")
        assert "Title" in result
        assert result.endswith(".mp4")
