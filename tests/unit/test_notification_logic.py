"""
Tests for notification triggering logic.

This module tests the is_error() function that determines whether
a Cloud Function response should trigger an error notification.

RULE: Any unexpected result is an error and must trigger notification.
"""

import pytest


def is_error(response: dict, status_code: int = 200) -> bool:
    """
    Determine if a response should be treated as an error requiring notification.

    An ERROR is any of:
    1. HTTP status >= 400
    2. Response contains 'error' field (single error)
    3. Response contains 'errors' field with critical errors
    4. Missing required fields (title, type)
    5. Invalid content type

    Args:
        response: The JSON response from Cloud Function
        status_code: HTTP status code (default 200)

    Returns:
        True if this should trigger an error notification
    """
    # HTTP errors always notify
    if status_code >= 400:
        return True

    # Single error field means notify
    if 'error' in response:
        return True

    # Multiple errors - check if any are critical
    if 'errors' in response:
        for error in response['errors']:
            # Transcription errors for podcasts are notable
            if error.get('stage') == 'transcription':
                return True
            # Non-recoverable errors are critical
            if error.get('recoverable') is False:
                return True

    # Missing or empty title is unexpected
    if not response.get('title'):
        return True

    # Missing or invalid type is unexpected
    valid_types = ['article', 'video', 'podcast', 'product', 'code', 'social', 'document']
    if response.get('type') not in valid_types:
        return True

    return False


class TestIsError:
    """Tests for the is_error() helper function."""

    # =========================================================================
    # HTTP Status Code Errors
    # =========================================================================

    def test_http_400_is_error(self):
        """HTTP 400 should trigger notification."""
        response = {'error': 'Missing required field: url'}
        assert is_error(response, 400) is True

    def test_http_404_is_error(self):
        """HTTP 404 should trigger notification."""
        response = {'error': 'Not found'}
        assert is_error(response, 404) is True

    def test_http_500_is_error(self):
        """HTTP 500 should trigger notification."""
        response = {'error': {'stage': 'processing', 'message': 'Crash'}}
        assert is_error(response, 500) is True

    def test_http_200_with_error_is_error(self):
        """HTTP 200 with error field should trigger notification."""
        response = {
            'url': 'https://example.com',
            'error': {'stage': 'fetch', 'message': 'Timeout'}
        }
        assert is_error(response, 200) is True

    # =========================================================================
    # Error Field Present
    # =========================================================================

    def test_error_field_triggers_notification(self):
        """Any response with error field triggers notification."""
        response = {
            'url': 'https://example.com',
            'domain': 'example.com',
            'type': 'article',
            'title': 'Test',
            'error': {'stage': 'ai_analysis', 'message': 'AI failed', 'recoverable': True}
        }
        assert is_error(response) is True

    def test_errors_with_transcription_failure_triggers_notification(self):
        """Transcription failures in errors array trigger notification."""
        response = {
            'url': 'https://open.spotify.com/episode/abc',
            'type': 'podcast',
            'title': 'Episode',
            'errors': [
                {'stage': 'transcription', 'message': 'No RSS', 'recoverable': True}
            ]
        }
        assert is_error(response) is True

    def test_errors_with_only_ai_failure_may_not_trigger(self):
        """AI-only failure in errors array may not trigger notification."""
        response = {
            'url': 'https://example.com/article',
            'type': 'article',
            'title': 'Good Article',
            'errors': [
                {'stage': 'ai_analysis', 'message': 'Gemini error', 'recoverable': True}
            ]
        }
        # AI failure alone with good title and type is borderline
        # Current implementation: only check transcription and non-recoverable
        assert is_error(response) is False  # May want to change this

    # =========================================================================
    # Missing Required Fields
    # =========================================================================

    def test_missing_title_is_error(self):
        """Missing title triggers notification."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': None,
        }
        assert is_error(response) is True

    def test_empty_title_is_error(self):
        """Empty string title triggers notification."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': '',
        }
        # Empty string is falsy, so None check catches it
        assert is_error(response) is True

    def test_missing_type_is_error(self):
        """Missing type triggers notification."""
        response = {
            'url': 'https://example.com',
            'title': 'Some Title',
            'type': None,
        }
        assert is_error(response) is True

    def test_invalid_type_is_error(self):
        """Invalid type triggers notification."""
        response = {
            'url': 'https://example.com',
            'title': 'Some Title',
            'type': 'unknown',
        }
        assert is_error(response) is True

    # =========================================================================
    # Valid Success Cases
    # =========================================================================

    def test_complete_article_is_not_error(self):
        """Complete article response is not an error."""
        response = {
            'url': 'https://example.com/article',
            'domain': 'example.com',
            'type': 'article',
            'title': 'Great Article',
            'author': 'John Doe',
            'reading_time': 5,
            'ai_summary': 'This is a summary',
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False

    def test_complete_video_is_not_error(self):
        """Complete video response is not an error."""
        response = {
            'url': 'https://tiktok.com/@user/video/123',
            'type': 'video',
            'title': 'Cool Video',
            'author': 'Creator',
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False

    def test_complete_podcast_is_not_error(self):
        """Complete podcast response is not an error."""
        response = {
            'url': 'https://open.spotify.com/episode/abc',
            'type': 'podcast',
            'title': 'Episode Title',
            'show_name': 'My Podcast',
            'transcription': 'Full transcription text...',
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False

    def test_product_with_price_is_not_error(self):
        """Product with extracted price is not an error."""
        response = {
            'url': 'https://amazon.com/dp/B00123',
            'type': 'product',
            'title': 'Widget Pro',
            'price': 29.99,
            'currency': 'USD',
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False

    def test_code_resource_is_not_error(self):
        """Code resource response is not an error."""
        response = {
            'url': 'https://github.com/user/repo',
            'type': 'code',
            'title': 'Repository Name',
            'code_snippets': ['print("hello")'],
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False

    def test_social_post_is_not_error(self):
        """Social post response is not an error."""
        response = {
            'url': 'https://twitter.com/user/status/123',
            'type': 'social',
            'title': 'Tweet Content',
            'processed_at': '2024-12-31T00:00:00Z'
        }
        assert is_error(response) is False


class TestEdgeCases:
    """Edge cases for error detection."""

    def test_partial_data_with_title_and_type_ok(self):
        """Partial data but with title and type is acceptable."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': 'Minimal Title',
            # Many fields missing but that's OK
        }
        assert is_error(response) is False

    def test_null_optional_fields_ok(self):
        """Null optional fields are acceptable."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': 'Test',
            'author': None,
            'reading_time': None,
            'ai_summary': None,
            'ai_analysis': None,
        }
        assert is_error(response) is False

    def test_empty_code_snippets_ok(self):
        """Empty code snippets for code type is acceptable."""
        response = {
            'url': 'https://stackoverflow.com/q/123',
            'type': 'code',
            'title': 'How to do X?',
            'code_snippets': [],
        }
        assert is_error(response) is False

    def test_zero_reading_time_ok(self):
        """Zero reading time is acceptable."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': 'Short Article',
            'reading_time': 0,
        }
        assert is_error(response) is False
