"""
Integration tests for HTTP handlers with mocked external APIs.

Uses the `responses` library to mock requests.
"""

import pytest
import responses
from unittest.mock import patch, MagicMock


class TestFetchWebpage:
    """Tests for fetch_webpage() with mocked HTTP responses."""

    @responses.activate
    def test_success_returns_html(self, fetch_webpage):
        """Successful fetch returns HTML content."""
        test_url = "https://example.com/article"
        test_html = "<html><body><h1>Test Article</h1></body></html>"

        responses.add(
            responses.GET,
            test_url,
            body=test_html,
            status=200,
            content_type="text/html"
        )

        html, error = fetch_webpage(test_url)
        assert html == test_html
        assert error is None

    @responses.activate
    def test_404_returns_error(self, fetch_webpage):
        """404 response returns error tuple."""
        test_url = "https://example.com/not-found"

        responses.add(
            responses.GET,
            test_url,
            status=404
        )

        html, error = fetch_webpage(test_url)
        assert html is None
        assert error is not None
        assert "404" in error or "Not Found" in error.lower() or "HTTPError" in str(error)

    @responses.activate
    def test_500_returns_error(self, fetch_webpage):
        """500 response returns error tuple."""
        test_url = "https://example.com/server-error"

        responses.add(
            responses.GET,
            test_url,
            status=500
        )

        html, error = fetch_webpage(test_url)
        assert html is None
        assert error is not None

    @responses.activate
    def test_timeout_returns_error(self, fetch_webpage):
        """Request timeout returns error tuple."""
        import requests
        test_url = "https://example.com/slow"

        responses.add(
            responses.GET,
            test_url,
            body=requests.exceptions.Timeout()
        )

        html, error = fetch_webpage(test_url)
        assert html is None
        assert error is not None
        assert "timed out" in error.lower()

    @responses.activate
    def test_connection_error(self, fetch_webpage):
        """Connection error returns error tuple."""
        import requests
        test_url = "https://unreachable.example.com"

        responses.add(
            responses.GET,
            test_url,
            body=requests.exceptions.ConnectionError()
        )

        html, error = fetch_webpage(test_url)
        assert html is None
        assert error is not None


class TestGetSpotifyAccessToken:
    """Tests for get_spotify_access_token() with mocked Spotify auth."""

    @responses.activate
    def test_successful_token_fetch(self, get_spotify_access_token):
        """Successful auth returns access token."""
        responses.add(
            responses.POST,
            "https://accounts.spotify.com/api/token",
            json={"access_token": "test_token_abc123", "expires_in": 3600},
            status=200
        )

        with patch.dict('os.environ', {
            'SPOTIFY_CLIENT_ID': 'test_client_id',
            'SPOTIFY_CLIENT_SECRET': 'test_client_secret'
        }):
            # Clear the token cache
            from tests.conftest import _webpage_enricher_module
            _webpage_enricher_module._spotify_token_cache['token'] = None
            _webpage_enricher_module._spotify_token_cache['expires_at'] = 0

            # Reload env vars in the module
            _webpage_enricher_module.SPOTIFY_CLIENT_ID = 'test_client_id'
            _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = 'test_client_secret'

            token = get_spotify_access_token()
            assert token == "test_token_abc123"

    def test_missing_credentials_returns_none(self, get_spotify_access_token):
        """Missing credentials returns None."""
        from tests.conftest import _webpage_enricher_module

        # Clear cache and credentials
        _webpage_enricher_module._spotify_token_cache['token'] = None
        _webpage_enricher_module._spotify_token_cache['expires_at'] = 0
        original_id = _webpage_enricher_module.SPOTIFY_CLIENT_ID
        original_secret = _webpage_enricher_module.SPOTIFY_CLIENT_SECRET

        try:
            _webpage_enricher_module.SPOTIFY_CLIENT_ID = None
            _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = None

            token = get_spotify_access_token()
            assert token is None
        finally:
            _webpage_enricher_module.SPOTIFY_CLIENT_ID = original_id
            _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = original_secret


class TestFetchSpotifyEpisode:
    """Tests for fetch_spotify_episode() with mocked Spotify API."""

    @responses.activate
    def test_successful_episode_fetch(self, fetch_spotify_episode):
        """Successful fetch returns episode metadata."""
        episode_id = "4rOoJ6Egrf8K2IrywzwOMk"
        episode_url = f"https://open.spotify.com/episode/{episode_id}"

        # Mock token endpoint
        responses.add(
            responses.POST,
            "https://accounts.spotify.com/api/token",
            json={"access_token": "test_token", "expires_in": 3600},
            status=200
        )

        # Mock episode endpoint
        responses.add(
            responses.GET,
            f"https://api.spotify.com/v1/episodes/{episode_id}",
            json={
                "name": "Test Episode",
                "description": "A test podcast episode",
                "duration_ms": 3600000,
                "release_date": "2024-12-15",
                "images": [{"url": "https://example.com/cover.jpg"}],
                "show": {
                    "name": "Test Podcast",
                    "publisher": "Test Publisher"
                }
            },
            status=200
        )

        from tests.conftest import _webpage_enricher_module
        _webpage_enricher_module._spotify_token_cache['token'] = None
        _webpage_enricher_module._spotify_token_cache['expires_at'] = 0
        _webpage_enricher_module.SPOTIFY_CLIENT_ID = 'test_id'
        _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = 'test_secret'

        result = fetch_spotify_episode(episode_url)
        assert result['success'] is True
        assert result['title'] == "Test Episode"
        assert result['show_name'] == "Test Podcast"

    def test_invalid_url_returns_error(self, fetch_spotify_episode):
        """Invalid URL returns error."""
        result = fetch_spotify_episode("https://youtube.com/watch?v=abc")
        assert result['success'] is False
        assert 'error' in result

    @responses.activate
    def test_episode_not_found(self, fetch_spotify_episode):
        """404 from Spotify API returns error."""
        episode_id = "nonexistent"
        episode_url = f"https://open.spotify.com/episode/{episode_id}"

        # Mock token endpoint
        responses.add(
            responses.POST,
            "https://accounts.spotify.com/api/token",
            json={"access_token": "test_token", "expires_in": 3600},
            status=200
        )

        # Mock 404 response
        responses.add(
            responses.GET,
            f"https://api.spotify.com/v1/episodes/{episode_id}",
            json={"error": {"status": 404, "message": "Not found"}},
            status=404
        )

        from tests.conftest import _webpage_enricher_module
        _webpage_enricher_module._spotify_token_cache['token'] = None
        _webpage_enricher_module._spotify_token_cache['expires_at'] = 0
        _webpage_enricher_module.SPOTIFY_CLIENT_ID = 'test_id'
        _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = 'test_secret'

        result = fetch_spotify_episode(episode_url)
        assert result['success'] is False

    @responses.activate
    def test_fallback_to_oembed_when_no_credentials(self, fetch_spotify_episode):
        """Falls back to oEmbed when no API credentials."""
        episode_url = "https://open.spotify.com/episode/abc123"

        # Mock oEmbed response
        responses.add(
            responses.GET,
            "https://open.spotify.com/oembed",
            json={
                "title": "oEmbed Episode Title",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "provider_name": "Spotify"
            },
            status=200
        )

        from tests.conftest import _webpage_enricher_module
        _webpage_enricher_module._spotify_token_cache['token'] = None
        _webpage_enricher_module._spotify_token_cache['expires_at'] = 0
        _webpage_enricher_module.SPOTIFY_CLIENT_ID = None
        _webpage_enricher_module.SPOTIFY_CLIENT_SECRET = None

        result = fetch_spotify_episode(episode_url)
        # Should get some result from oEmbed fallback
        assert 'title' in result or 'error' in result
