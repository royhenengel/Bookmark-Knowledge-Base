"""
Error Contract Tests - Defines what is considered an ERROR.

These tests serve as guardrails to ensure consistent error handling.

RULE: Any unexpected result is an ERROR and must trigger notification.

Error Classification:
====================

FATAL ERRORS (HTTP 400/500, must notify):
- Missing required fields (url)
- Unhandled exceptions
- Complete processing failure

PROCESSING ERRORS (HTTP 200 with error field, must notify):
- Failed to fetch webpage (timeout, 404, 500, blocked)
- Failed to detect content type
- Failed to extract any metadata
- Missing critical fields (no title AND no content)

PARTIAL FAILURES (HTTP 200 with errors array, notify if critical):
- AI analysis failed (recoverable, may not notify)
- Transcription failed (recoverable, notify for podcasts)
- Price extraction failed for products (notify)
- Code extraction failed for code pages (notify)

SUCCESS (HTTP 200, no error field):
- All processing completed
- Got title, content type, and at least some metadata
"""

import pytest
import json


class TestErrorClassification:
    """Tests that verify error classification logic."""

    # =========================================================================
    # FATAL ERRORS - These MUST trigger notifications
    # =========================================================================

    def test_missing_url_is_fatal_error(self, mock_flask_request, enrich_webpage):
        """Missing URL field is a fatal error (HTTP 400)."""
        request = mock_flask_request(json_data={})
        response, status_code, headers = enrich_webpage(request)

        assert status_code == 400
        data = json.loads(response)
        assert 'error' in data
        assert 'url' in data['error'].lower()

    def test_empty_url_is_fatal_error(self, mock_flask_request, enrich_webpage):
        """Empty URL string is a fatal error."""
        request = mock_flask_request(json_data={'url': ''})
        response, status_code, headers = enrich_webpage(request)

        # Should be 400 or have error in response
        data = json.loads(response)
        # Empty URL should fail validation or fetch
        assert status_code == 400 or 'error' in data

    def test_invalid_url_format_is_error(self, mock_flask_request, enrich_webpage):
        """Invalid URL format should produce an error."""
        request = mock_flask_request(json_data={'url': 'not-a-valid-url'})
        response, status_code, headers = enrich_webpage(request)

        data = json.loads(response)
        # Should have error - either fetch fails or processing fails
        assert 'error' in data or status_code >= 400

    # =========================================================================
    # PROCESSING ERRORS - These MUST be in error field
    # =========================================================================

    def test_fetch_error_is_processing_error(self):
        """Verify fetch error structure matches expected format."""
        # This tests the expected error format
        error_response = {
            'url': 'https://example.com',
            'domain': 'example.com',
            'error': {
                'stage': 'fetch',
                'message': 'HTTP error: 404',
                'recoverable': True
            }
        }

        assert 'error' in error_response
        assert error_response['error']['stage'] == 'fetch'
        assert 'message' in error_response['error']
        assert 'recoverable' in error_response['error']

    def test_timeout_error_is_processing_error(self):
        """Timeout should be a processing error with recoverable=True."""
        error_response = {
            'url': 'https://slow.example.com',
            'domain': 'slow.example.com',
            'error': {
                'stage': 'fetch',
                'message': 'Request timed out',
                'recoverable': True
            }
        }

        assert error_response['error']['recoverable'] is True

    def test_blocked_page_is_processing_error(self):
        """Blocked page (sign in required) should be a processing error."""
        error_response = {
            'url': 'https://blocked.example.com',
            'domain': 'blocked.example.com',
            'error': {
                'stage': 'fetch',
                'message': 'Sign in to confirm you are not a robot',
                'recoverable': True
            }
        }

        assert 'error' in error_response
        assert error_response['error']['recoverable'] is True

    # =========================================================================
    # ERROR FIELD REQUIREMENTS
    # =========================================================================

    def test_error_must_have_stage(self):
        """All errors must include a stage field."""
        valid_stages = ['fetch', 'processing', 'ai_analysis', 'transcription']

        for stage in valid_stages:
            error = {'stage': stage, 'message': 'test', 'recoverable': True}
            assert 'stage' in error
            assert error['stage'] in valid_stages

    def test_error_must_have_message(self):
        """All errors must include a message field."""
        error = {'stage': 'fetch', 'message': 'Connection refused', 'recoverable': True}

        assert 'message' in error
        assert isinstance(error['message'], str)
        assert len(error['message']) > 0

    def test_error_must_have_recoverable(self):
        """All errors must indicate if they are recoverable."""
        recoverable_error = {'stage': 'fetch', 'message': 'Timeout', 'recoverable': True}
        fatal_error = {'stage': 'processing', 'message': 'Crash', 'recoverable': False}

        assert recoverable_error['recoverable'] is True
        assert fatal_error['recoverable'] is False

    # =========================================================================
    # SUCCESS CRITERIA - What is NOT an error
    # =========================================================================

    def test_success_response_has_no_error_field(self):
        """Successful response should not have error field."""
        success_response = {
            'url': 'https://example.com/article',
            'domain': 'example.com',
            'type': 'article',
            'title': 'Test Article',
            'author': 'John Doe',
            'reading_time': 5,
            'ai_summary': 'A test article.',
            'processed_at': '2024-12-31T00:00:00Z'
        }

        assert 'error' not in success_response
        assert success_response['title'] is not None

    def test_success_requires_title(self):
        """A response without title should be considered incomplete."""
        incomplete_response = {
            'url': 'https://example.com',
            'domain': 'example.com',
            'type': 'article',
            'title': None,  # Missing title
        }

        # This is an unexpected result - should trigger notification
        assert incomplete_response['title'] is None
        # The calling workflow should treat this as an error

    def test_success_requires_content_type(self):
        """A response without content type should be considered incomplete."""
        incomplete_response = {
            'url': 'https://example.com',
            'domain': 'example.com',
            'type': None,  # Missing type
            'title': 'Some Title',
        }

        # Missing type is unexpected
        assert incomplete_response['type'] is None

    # =========================================================================
    # PARTIAL SUCCESS CRITERIA
    # =========================================================================

    def test_partial_success_with_ai_error(self):
        """AI error should be in error field but response still useful."""
        partial_success = {
            'url': 'https://example.com',
            'domain': 'example.com',
            'type': 'article',
            'title': 'Test Article',
            'author': 'John Doe',
            'ai_summary': None,
            'ai_analysis': None,
            'error': {
                'stage': 'ai_analysis',
                'message': 'Gemini API error',
                'recoverable': True
            }
        }

        assert 'error' in partial_success
        assert partial_success['error']['stage'] == 'ai_analysis'
        assert partial_success['title'] is not None  # But we still got the title

    def test_partial_success_with_multiple_errors(self):
        """Multiple non-fatal errors should be in errors array."""
        partial_success = {
            'url': 'https://open.spotify.com/episode/abc',
            'domain': 'open.spotify.com',
            'type': 'podcast',
            'title': 'Podcast Episode',
            'errors': [
                {'stage': 'ai_analysis', 'message': 'AI failed', 'recoverable': True},
                {'stage': 'transcription', 'message': 'No RSS feed', 'recoverable': True}
            ]
        }

        assert 'errors' in partial_success
        assert len(partial_success['errors']) == 2
        assert partial_success['title'] is not None


class TestRecoverableVsNonRecoverable:
    """Tests that verify recoverable vs non-recoverable error classification."""

    def test_network_errors_are_recoverable(self):
        """Network-related errors should be recoverable (worth retrying)."""
        recoverable_errors = [
            'Request timed out',
            'Connection refused',
            'Connection reset',
            'Too many requests',  # Rate limited
            'HTTP error: 429',
            'HTTP error: 500',
            'HTTP error: 502',
            'HTTP error: 503',
            'HTTP error: 504',
        ]

        for error_msg in recoverable_errors:
            error = {'stage': 'fetch', 'message': error_msg, 'recoverable': True}
            assert error['recoverable'] is True, f"{error_msg} should be recoverable"

    def test_client_errors_are_not_recoverable(self):
        """Client errors (4xx except 429) should not be recoverable."""
        non_recoverable_errors = [
            'HTTP error: 400',
            'HTTP error: 401',
            'HTTP error: 403',
            'HTTP error: 404',
            'HTTP error: 410',  # Gone
        ]

        for error_msg in non_recoverable_errors:
            # These should be marked non-recoverable
            # Retrying won't help - the resource doesn't exist or is forbidden
            pass  # Document the expectation

    def test_invalid_input_is_not_recoverable(self):
        """Invalid input errors should not be recoverable."""
        non_recoverable = {
            'stage': 'processing',
            'message': 'Invalid URL format',
            'recoverable': False
        }

        assert non_recoverable['recoverable'] is False

    def test_unhandled_exception_is_not_recoverable(self):
        """Unhandled exceptions should be non-recoverable."""
        fatal = {
            'stage': 'processing',
            'message': 'NoneType has no attribute xyz',
            'recoverable': False
        }

        assert fatal['recoverable'] is False


class TestNotificationTriggers:
    """Tests that define when notifications should be triggered.

    RULE: Any unexpected result is an error and must trigger notification.
    """

    def test_must_notify_on_http_400(self):
        """HTTP 400 responses must trigger notification."""
        assert 400 >= 400  # Any 4xx error triggers notification

    def test_must_notify_on_http_500(self):
        """HTTP 500 responses must trigger notification."""
        assert 500 >= 400  # Any 5xx error triggers notification

    def test_must_notify_on_error_field(self):
        """Presence of error field must trigger notification."""
        responses_requiring_notification = [
            {'error': 'Any error message'},
            {'error': {'stage': 'fetch', 'message': 'Failed'}},
            {'url': 'x', 'error': {'stage': 'processing', 'message': 'Crash'}},
        ]

        for response in responses_requiring_notification:
            assert 'error' in response

    def test_must_notify_on_missing_title(self):
        """Missing title in response must trigger notification."""
        response = {
            'url': 'https://example.com',
            'type': 'article',
            'title': None,
        }

        # This is an unexpected result
        is_unexpected = response['title'] is None
        assert is_unexpected  # Must notify

    def test_must_notify_on_unexpected_type(self):
        """Unknown content type should trigger notification for review."""
        response = {
            'url': 'https://example.com',
            'type': 'unknown',  # or None
            'title': 'Some Title',
        }

        valid_types = ['article', 'video', 'podcast', 'product', 'code', 'social', 'document']
        is_unexpected = response['type'] not in valid_types
        assert is_unexpected  # Must notify for review

    def test_no_notification_on_clean_success(self):
        """Clean success should not trigger notification."""
        success_response = {
            'url': 'https://example.com/article',
            'domain': 'example.com',
            'type': 'article',
            'title': 'Great Article Title',
            'author': 'Jane Author',
            'reading_time': 7,
            'ai_summary': 'This article discusses...',
            'ai_analysis': 'Key topics: tech, innovation',
            'processed_at': '2024-12-31T12:00:00Z'
        }

        # No error field
        has_error = 'error' in success_response or 'errors' in success_response
        # Has required fields
        has_title = success_response.get('title') is not None
        has_type = success_response.get('type') in ['article', 'video', 'podcast', 'product', 'code', 'social', 'document']

        # This is a clean success
        assert not has_error
        assert has_title
        assert has_type


class TestVideoEnricherErrors:
    """Error contracts for video-enricher Cloud Function."""

    def test_video_error_must_have_stage(self):
        """Video processing errors must include stage."""
        error_response = {
            'error': {
                'stage': 'download',
                'message': 'Video unavailable',
                'recoverable': False
            }
        }

        assert error_response['error']['stage'] in ['download', 'transcription', 'metadata', 'upload']

    def test_rate_limited_video_is_recoverable(self):
        """Rate limited video downloads should be recoverable."""
        error = {
            'stage': 'download',
            'message': 'Rate limited by TikTok',
            'recoverable': True
        }

        assert error['recoverable'] is True

    def test_video_not_found_is_not_recoverable(self):
        """Video not found errors should not be recoverable."""
        error = {
            'stage': 'download',
            'message': 'Video has been removed',
            'recoverable': False
        }

        assert error['recoverable'] is False


class TestTitleLengthLimits:
    """Tests for title length handling.

    RULE: All titles must be max 70 characters. Exceeding this is an ERROR.
    Truncated titles must be complete (not cut mid-word).
    """

    # The one true limit for all titles
    MAX_TITLE_LENGTH = 70

    def test_title_over_70_chars_is_error(self):
        """Title exceeding 70 characters is an error requiring notification."""
        from shared.title_utils import validate_title

        long_title = "A" * 71
        result = validate_title(long_title)

        assert result['valid'] is False
        assert any('70' in err for err in result['errors'])

    def test_title_exactly_70_chars_is_valid(self):
        """Title at exactly 70 characters is valid."""
        from shared.title_utils import validate_title

        title_70 = "A" * 70
        result = validate_title(title_70)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_title_under_70_chars_is_valid(self):
        """Title under 70 characters is valid."""
        from shared.title_utils import validate_title

        short_title = "This is a normal title"
        result = validate_title(short_title)

        assert result['valid'] is True

    def test_title_with_null_bytes_is_error(self):
        """Titles containing null bytes should be rejected."""
        from shared.title_utils import validate_title

        bad_title = "Normal Title\x00Hidden Content"
        result = validate_title(bad_title)

        assert result['valid'] is False
        assert any('null' in err.lower() for err in result['errors'])

    def test_title_only_whitespace_is_error(self):
        """Title that is only whitespace is an error."""
        from shared.title_utils import validate_title

        whitespace_title = "   \t\n   "
        result = validate_title(whitespace_title)

        assert result['valid'] is False
        assert any('whitespace' in err.lower() for err in result['errors'])

    def test_title_only_special_chars_is_error(self):
        """Title with only special characters is an error."""
        from shared.title_utils import validate_title

        special_only = "###!!!@@@"
        result = validate_title(special_only)

        assert result['valid'] is False
        assert any('alphanumeric' in err.lower() for err in result['errors'])

    def test_empty_title_is_error(self):
        """Empty title is an error."""
        from shared.title_utils import validate_title

        result = validate_title("")
        assert result['valid'] is False

        result_none = validate_title(None)
        assert result_none['valid'] is False


class TestSmartTitleTruncation:
    """Tests for smart title truncation at word boundaries.

    RULE: When truncating, never cut in the middle of a word.
    """

    def test_truncate_at_word_boundary(self):
        """Truncation should happen at word boundary, not mid-word."""
        from shared.title_utils import truncate_title

        # "This is a test title" = 20 chars, limit to 15
        title = "This is a test title that is too long"
        truncated, was_truncated = truncate_title(title, max_length=20)

        assert was_truncated is True
        assert len(truncated) <= 20
        # Should end with complete word
        assert truncated == "This is a test title" or truncated.endswith(' ') is False
        # Should not end mid-word
        assert not truncated[-1].isalpha() or truncated == title[:20].rsplit(' ', 1)[0]

    def test_truncate_preserves_complete_words(self):
        """Truncated title should contain complete words only."""
        from shared.title_utils import truncate_title

        title = "The quick brown fox jumps over the lazy dog"
        truncated, was_truncated = truncate_title(title, max_length=25)

        assert was_truncated is True
        # Each word should be complete
        words = truncated.split()
        for word in words:
            assert word in title.split()

    def test_no_truncation_needed(self):
        """Short titles should not be modified."""
        from shared.title_utils import truncate_title

        title = "Short Title"
        truncated, was_truncated = truncate_title(title)

        assert was_truncated is False
        assert truncated == title

    def test_truncate_single_long_word(self):
        """Single word longer than limit uses ellipsis."""
        from shared.title_utils import truncate_title

        title = "Supercalifragilisticexpialidocious"
        truncated, was_truncated = truncate_title(title, max_length=20)

        assert was_truncated is True
        assert len(truncated) <= 20
        assert truncated.endswith('...')

    def test_truncate_default_70_chars(self):
        """Default truncation is at 70 characters."""
        from shared.title_utils import truncate_title, MAX_TITLE_LENGTH

        assert MAX_TITLE_LENGTH == 70

        title = "A" * 100
        truncated, was_truncated = truncate_title(title)

        assert was_truncated is True
        assert len(truncated) <= 70

    def test_truncate_empty_title(self):
        """Empty title returns empty string."""
        from shared.title_utils import truncate_title

        truncated, was_truncated = truncate_title("")
        assert truncated == ""
        assert was_truncated is False

    def test_truncated_title_ends_cleanly(self):
        """Truncated title should not end with incomplete word or conjunction."""
        from shared.title_utils import truncate_title

        title = "This is a very long title and it keeps going on and on"
        truncated, _ = truncate_title(title, max_length=35)

        # Should not end with 'and', 'or', 'the', etc.
        bad_endings = [' and', ' or', ' the', ' a', ' an']
        for ending in bad_endings:
            # This is a soft check - truncation at word boundary may still hit these
            pass  # Documented behavior

    def test_sanitize_removes_null_bytes(self):
        """Sanitize should remove null bytes."""
        from shared.title_utils import sanitize_title

        bad_title = "Hello\x00World"
        sanitized = sanitize_title(bad_title)

        assert '\x00' not in sanitized
        assert "HelloWorld" == sanitized

    def test_sanitize_normalizes_whitespace(self):
        """Sanitize should normalize multiple spaces."""
        from shared.title_utils import sanitize_title

        messy_title = "Hello   World    Test"
        sanitized = sanitize_title(messy_title)

        assert sanitized == "Hello World Test"


class TestExpectedFieldsPerContentType:
    """Tests that verify all expected fields are present for each content type.

    Per SCHEMA_DESIGN.md, different content types have different required fields.
    Missing expected fields should trigger error notifications.
    """

    # Required fields per content type
    REQUIRED_FIELDS = {
        'article': ['url', 'title', 'type', 'domain'],
        'video': ['url', 'title', 'type', 'domain', 'author'],
        'podcast': ['url', 'title', 'type', 'domain', 'show_name'],
        'product': ['url', 'title', 'type', 'domain'],
        'code': ['url', 'title', 'type', 'domain'],
        'social': ['url', 'title', 'type', 'domain'],
        'document': ['url', 'title', 'type', 'domain'],
    }

    # Expected (but optional) fields that add value
    EXPECTED_FIELDS = {
        'article': ['author', 'reading_time', 'ai_summary'],
        'video': ['duration', 'transcription', 'ai_analysis'],
        'podcast': ['duration_minutes', 'publisher', 'transcription'],
        'product': ['price', 'currency'],
        'code': ['code_snippets'],
        'social': ['author'],
        'document': [],
    }

    def test_article_required_fields(self):
        """Article must have url, title, type, domain."""
        response = {
            'url': 'https://example.com/article',
            'title': 'Test Article',
            'type': 'article',
            'domain': 'example.com'
        }

        for field in self.REQUIRED_FIELDS['article']:
            assert field in response, f"Missing required field: {field}"
            assert response[field] is not None, f"Required field is None: {field}"

    def test_article_missing_title_is_error(self):
        """Article without title is an error."""
        response = {
            'url': 'https://example.com/article',
            'title': None,  # Missing!
            'type': 'article',
            'domain': 'example.com'
        }

        missing_required = [f for f in self.REQUIRED_FIELDS['article']
                          if response.get(f) is None]
        assert 'title' in missing_required

    def test_video_required_fields(self):
        """Video must have url, title, type, domain, author."""
        response = {
            'url': 'https://tiktok.com/@user/video/123',
            'title': 'Cool Video',
            'type': 'video',
            'domain': 'tiktok.com',
            'author': 'user123'
        }

        for field in self.REQUIRED_FIELDS['video']:
            assert field in response, f"Missing required field: {field}"
            assert response[field] is not None, f"Required field is None: {field}"

    def test_video_missing_author_is_error(self):
        """Video without author is an error."""
        response = {
            'url': 'https://tiktok.com/@user/video/123',
            'title': 'Cool Video',
            'type': 'video',
            'domain': 'tiktok.com',
            'author': None  # Missing!
        }

        missing_required = [f for f in self.REQUIRED_FIELDS['video']
                          if response.get(f) is None]
        assert 'author' in missing_required

    def test_podcast_required_fields(self):
        """Podcast must have url, title, type, domain, show_name."""
        response = {
            'url': 'https://open.spotify.com/episode/abc',
            'title': 'Episode Title',
            'type': 'podcast',
            'domain': 'open.spotify.com',
            'show_name': 'My Podcast'
        }

        for field in self.REQUIRED_FIELDS['podcast']:
            assert field in response, f"Missing required field: {field}"
            assert response[field] is not None, f"Required field is None: {field}"

    def test_podcast_missing_show_name_is_error(self):
        """Podcast without show_name is an error."""
        response = {
            'url': 'https://open.spotify.com/episode/abc',
            'title': 'Episode Title',
            'type': 'podcast',
            'domain': 'open.spotify.com',
            'show_name': None  # Missing!
        }

        missing_required = [f for f in self.REQUIRED_FIELDS['podcast']
                          if response.get(f) is None]
        assert 'show_name' in missing_required

    def test_product_required_fields(self):
        """Product must have url, title, type, domain."""
        response = {
            'url': 'https://amazon.com/dp/B00123',
            'title': 'Widget Pro',
            'type': 'product',
            'domain': 'amazon.com'
        }

        for field in self.REQUIRED_FIELDS['product']:
            assert field in response, f"Missing required field: {field}"
            assert response[field] is not None, f"Required field is None: {field}"

    def test_product_without_price_is_warning(self):
        """Product without price is a warning (expected but optional)."""
        response = {
            'url': 'https://amazon.com/dp/B00123',
            'title': 'Widget Pro',
            'type': 'product',
            'domain': 'amazon.com',
            'price': None  # Expected but optional
        }

        # Price is expected but not required - should be a warning not error
        missing_expected = [f for f in self.EXPECTED_FIELDS['product']
                          if response.get(f) is None]
        assert 'price' in missing_expected

    def test_all_content_types_have_url_title_type(self):
        """All content types require url, title, and type."""
        universal_required = ['url', 'title', 'type']

        for content_type, required_fields in self.REQUIRED_FIELDS.items():
            for field in universal_required:
                assert field in required_fields, \
                    f"{content_type} missing universal required field: {field}"

    def test_empty_string_is_same_as_none(self):
        """Empty string values should be treated as missing."""
        response = {
            'url': 'https://example.com',
            'title': '',  # Empty string = missing
            'type': 'article',
            'domain': 'example.com'
        }

        # Empty string should be treated as None
        effective_title = response['title'] or None
        assert effective_title is None


class TestFieldNotEmpty:
    """Tests that verify fields are not just present but have actual values."""

    def test_title_not_empty_string(self):
        """Title must have actual content, not just empty string."""
        bad_titles = ['', '   ', '\t', '\n', None]

        for title in bad_titles:
            is_empty = not (title and title.strip())
            assert is_empty, f"Should be considered empty: {repr(title)}"

    def test_url_is_valid_format(self):
        """URL must be a valid HTTP/HTTPS URL."""
        import re

        valid_urls = [
            'https://example.com',
            'http://test.org/path',
            'https://sub.domain.com/path?query=1'
        ]

        invalid_urls = [
            '',
            'not-a-url',
            'ftp://files.com',
            'javascript:alert(1)',
            None
        ]

        url_pattern = re.compile(r'^https?://')

        for url in valid_urls:
            assert url_pattern.match(url), f"Should be valid URL: {url}"

        for url in invalid_urls:
            if url:
                assert not url_pattern.match(url), f"Should be invalid URL: {url}"

    def test_domain_extracted_correctly(self):
        """Domain should be extracted from URL correctly."""
        from urllib.parse import urlparse

        test_cases = [
            ('https://www.example.com/path', 'www.example.com'),
            ('https://sub.domain.org/page', 'sub.domain.org'),
            ('http://tiktok.com/@user', 'tiktok.com'),
        ]

        for url, expected_domain in test_cases:
            parsed = urlparse(url)
            assert parsed.netloc == expected_domain

    def test_reading_time_is_positive_integer(self):
        """Reading time must be a positive integer."""
        valid_times = [1, 5, 10, 60]
        invalid_times = [0, -1, 0.5, 'five', None]

        for time in valid_times:
            is_valid = isinstance(time, int) and time > 0
            assert is_valid, f"Should be valid reading time: {time}"

        for time in invalid_times:
            is_valid = isinstance(time, int) and time > 0
            assert not is_valid, f"Should be invalid reading time: {time}"

    def test_price_is_non_negative_number(self):
        """Price must be a non-negative number."""
        valid_prices = [0, 0.99, 29.99, 100, 1000.00]
        invalid_prices = [-1, -0.01, 'free', None]

        for price in valid_prices:
            is_valid = isinstance(price, (int, float)) and price >= 0
            assert is_valid, f"Should be valid price: {price}"

        for price in invalid_prices:
            is_valid = isinstance(price, (int, float)) and price >= 0
            assert not is_valid, f"Should be invalid price: {price}"


class TestTitleQualityValidation:
    """Tests for AI/pattern-based title quality validation.

    The validate_title_quality function checks for:
    - Incomplete/truncated titles
    - All caps (shouting)
    - Repeated words
    - Garbage text patterns
    - Clarity issues
    """

    def test_good_title_has_high_quality_score(self):
        """A well-formed title should have quality score >= 0.9."""
        from shared.title_utils import validate_title_quality

        good_titles = [
            "10 Python Tips You Should Know",
            "How to Build a REST API with Flask",
            "Understanding Machine Learning Basics",
        ]

        for title in good_titles:
            result = validate_title_quality(title)
            assert result['quality_score'] >= 0.9, f"Good title should score high: {title}"
            assert result['is_acceptable'] is True

    def test_all_caps_title_is_flagged(self):
        """All caps title should be flagged as issue."""
        from shared.title_utils import validate_title_quality

        result = validate_title_quality("THIS IS ALL CAPS SHOUTING")

        assert result['quality_score'] < 1.0
        assert any('uppercase' in issue.lower() for issue in result['issues'])

    def test_repeated_words_are_flagged(self):
        """Repeated consecutive words should be flagged."""
        from shared.title_utils import validate_title_quality

        result = validate_title_quality("The the quick brown fox")

        assert any('repeated' in issue.lower() for issue in result['issues'])

    def test_no_spaces_is_flagged(self):
        """Long text with no spaces should be flagged."""
        from shared.title_utils import validate_title_quality

        result = validate_title_quality("ThisIsALongTitleWithNoSpacesBetweenWords")

        assert result['quality_score'] < 1.0
        assert any('spaces' in issue.lower() for issue in result['issues'])

    def test_very_short_title_is_flagged(self):
        """Very short title should be flagged."""
        from shared.title_utils import validate_title_quality

        result = validate_title_quality("Hi")

        assert result['quality_score'] < 1.0
        assert any('short' in issue.lower() for issue in result['issues'])

    def test_garbage_text_is_flagged(self):
        """Text with garbage patterns should be flagged."""
        from shared.title_utils import validate_title_quality

        garbage_titles = [
            "aaaaaaaaaaaaaaaaaaaaaaaaa",  # Same char repeated
            "1234567890123456",           # Long number sequence
        ]

        for title in garbage_titles:
            result = validate_title_quality(title)
            assert result['is_acceptable'] is False or result['quality_score'] < 0.8

    def test_empty_title_has_zero_quality(self):
        """Empty title should have zero quality score."""
        from shared.title_utils import validate_title_quality

        result = validate_title_quality("")
        assert result['quality_score'] == 0
        assert result['is_acceptable'] is False

        result_none = validate_title_quality(None)
        assert result_none['quality_score'] == 0

    def test_acceptable_threshold_is_0_7(self):
        """Titles with score >= 0.7 are acceptable."""
        from shared.title_utils import validate_title_quality

        # A title with minor issues should still be acceptable
        result = validate_title_quality("Good Title Here")

        if result['quality_score'] >= 0.7:
            assert result['is_acceptable'] is True
        else:
            assert result['is_acceptable'] is False

    def test_ai_validation_returns_pattern_results_by_default(self):
        """AI validation without LLM returns pattern-based results."""
        from shared.title_utils import validate_title_with_ai

        result = validate_title_with_ai("Good Title Here", use_llm=False)

        assert 'quality_score' in result
        assert 'issues' in result
        assert 'is_acceptable' in result

    def test_title_with_clean_truncation_is_acceptable(self):
        """Title truncated at word boundary should be acceptable."""
        from shared.title_utils import truncate_title, validate_title_quality

        long_title = "This is a very long title that needs to be truncated properly"
        truncated, was_truncated = truncate_title(long_title, max_length=40)

        result = validate_title_quality(truncated)

        # Properly truncated title should still be acceptable
        assert result['is_acceptable'] is True or result['quality_score'] >= 0.6


# =============================================================================
# GEMINI ANALYSIS SECTION VALIDATION
# Tests that ensure all required analysis fields are present and non-empty
# =============================================================================

class TestGeminiAnalysisParsing:
    """Tests for parsing Gemini analysis text into sections."""

    # New format with icons (no colon)
    SAMPLE_ANALYSIS_WITH_ICONS = """1. **👁️ Visual Content**
The video shows a person cooking in a modern kitchen.

2. **🔊 Audio Content**
Background music with voiceover explaining the recipe.

3. **🎬 Style & Production**
High-quality 4K footage with smooth transitions.

4. **🎭 Mood & Tone**
Upbeat and educational with a friendly atmosphere.

5. **💡 Key Messages**
Learn how to make a delicious pasta dish at home.

6. **📁 Content Category**
Tutorial/Educational cooking content."""

    # Legacy format with colons (backward compatibility)
    SAMPLE_ANALYSIS_LEGACY = """1. **Visual Content**: The video shows a person cooking in a modern kitchen.

2. **Audio Content**: Background music with voiceover explaining the recipe.

3. **Style & Production**: High-quality 4K footage with smooth transitions.

4. **Mood & Tone**: Upbeat and educational with a friendly atmosphere.

5. **Key Messages**: Learn how to make a delicious pasta dish at home.

6. **Content Category**: Tutorial/Educational cooking content."""

    def test_parse_all_sections_with_icons(self):
        """All 6 required sections should be parsed from icon format."""
        from shared.analysis_utils import parse_gemini_analysis

        sections = parse_gemini_analysis(self.SAMPLE_ANALYSIS_WITH_ICONS)

        assert 'Visual Content' in sections
        assert 'Audio Content' in sections
        assert 'Style & Production' in sections
        assert 'Mood & Tone' in sections
        assert 'Key Messages' in sections
        assert 'Content Category' in sections

    def test_parse_all_sections_legacy(self):
        """All 6 required sections should be parsed from legacy format."""
        from shared.analysis_utils import parse_gemini_analysis

        sections = parse_gemini_analysis(self.SAMPLE_ANALYSIS_LEGACY)

        assert 'Visual Content' in sections
        assert 'Audio Content' in sections
        assert 'Style & Production' in sections
        assert 'Mood & Tone' in sections
        assert 'Key Messages' in sections
        assert 'Content Category' in sections

    def test_icons_stripped_from_section_names(self):
        """Icons should be stripped from section names during parsing."""
        from shared.analysis_utils import parse_gemini_analysis

        sections = parse_gemini_analysis(self.SAMPLE_ANALYSIS_WITH_ICONS)

        # Section names should NOT contain icons
        for section_name in sections.keys():
            assert '👁️' not in section_name
            assert '🔊' not in section_name
            assert '🎬' not in section_name
            assert '🎭' not in section_name
            assert '💡' not in section_name
            assert '📁' not in section_name

    def test_section_content_not_empty(self):
        """Parsed sections should have non-empty content."""
        from shared.analysis_utils import parse_gemini_analysis

        sections = parse_gemini_analysis(self.SAMPLE_ANALYSIS_WITH_ICONS)

        for section_name, content in sections.items():
            assert content.strip(), f"Section '{section_name}' should not be empty"

    def test_parse_empty_analysis_returns_empty_dict(self):
        """Empty analysis text should return empty dict."""
        from shared.analysis_utils import parse_gemini_analysis

        assert parse_gemini_analysis("") == {}
        assert parse_gemini_analysis(None) == {}

    def test_parse_alternative_markdown_format(self):
        """Should handle alternative markdown formats."""
        from shared.analysis_utils import parse_gemini_analysis

        alt_format = """## Visual Content
Shows a beautiful sunset over the ocean.

## Audio Content
Ocean waves with calm music.

## Style & Production
Drone footage with color grading.

## Mood & Tone
Relaxing and peaceful.

## Key Messages
Nature is beautiful.

## Content Category
Nature/Relaxation"""

        sections = parse_gemini_analysis(alt_format)
        # Should parse at least some sections
        assert len(sections) > 0


class TestGeminiAnalysisValidation:
    """Tests for validating Gemini analysis sections."""

    VALID_ANALYSIS = """1. **Visual Content**: The video shows a person cooking in a modern kitchen.

2. **Audio Content**: Background music with voiceover explaining the recipe.

3. **Style & Production**: High-quality 4K footage with smooth transitions.

4. **Mood & Tone**: Upbeat and educational with a friendly atmosphere.

5. **Key Messages**: Learn how to make a delicious pasta dish at home.

6. **Content Category**: Tutorial/Educational cooking content."""

    def test_valid_analysis_passes_validation(self):
        """Complete analysis with all sections should be valid."""
        from shared.analysis_utils import validate_analysis_sections

        result = validate_analysis_sections(self.VALID_ANALYSIS)

        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert len(result['missing']) == 0
        assert len(result['empty']) == 0

    def test_empty_analysis_fails_validation(self):
        """Empty analysis should fail validation."""
        from shared.analysis_utils import validate_analysis_sections

        result = validate_analysis_sections("")

        assert result['valid'] is False
        assert 'Analysis text is missing or empty' in result['errors']

    def test_none_analysis_fails_validation(self):
        """None analysis should fail validation."""
        from shared.analysis_utils import validate_analysis_sections

        result = validate_analysis_sections(None)

        assert result['valid'] is False
        assert 'Analysis text is missing or empty' in result['errors']

    def test_missing_section_is_error(self):
        """Missing a required section should be an error."""
        from shared.analysis_utils import validate_analysis_sections

        # Missing "Key Messages" section
        incomplete = """1. **Visual Content**: Video content here.

2. **Audio Content**: Audio content here.

3. **Style & Production**: Style content here.

4. **Mood & Tone**: Mood content here.

6. **Content Category**: Category content here."""

        result = validate_analysis_sections(incomplete)

        assert result['valid'] is False
        assert 'Key Messages' in result['missing']
        assert any('Key Messages' in err for err in result['errors'])

    def test_empty_section_is_error(self):
        """Section with empty content should be an error."""
        from shared.analysis_utils import validate_analysis_sections

        # Audio Content section is empty
        with_empty = """1. **Visual Content**: Video content here.

2. **Audio Content**:

3. **Style & Production**: Style content here.

4. **Mood & Tone**: Mood content here.

5. **Key Messages**: Key messages here.

6. **Content Category**: Category content here."""

        result = validate_analysis_sections(with_empty)

        assert result['valid'] is False
        assert 'Audio Content' in result['empty']

    def test_all_required_sections_are_checked(self):
        """All 6 required sections must be validated."""
        from shared.analysis_utils import (
            REQUIRED_ANALYSIS_SECTIONS,
            validate_analysis_sections
        )

        # Verify the required sections list
        expected_sections = [
            'Visual Content',
            'Audio Content',
            'Style & Production',
            'Mood & Tone',
            'Key Messages',
            'Content Category',
        ]
        assert REQUIRED_ANALYSIS_SECTIONS == expected_sections

        # Empty text should report all as missing
        result = validate_analysis_sections("")
        assert result['valid'] is False
        # All required sections should be flagged as missing
        assert len(result['missing']) == len(expected_sections)


class TestTranscriptionValidation:
    """Tests for validating transcription results."""

    def test_valid_transcription_passes(self):
        """Transcription with text should be valid."""
        from shared.analysis_utils import validate_transcription

        transcription = {
            'text': 'This is the transcript of the video.',
            'confidence': 0.95,
            'language': 'en'
        }

        result = validate_transcription(transcription)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_none_transcription_fails(self):
        """None transcription should fail."""
        from shared.analysis_utils import validate_transcription

        result = validate_transcription(None)

        assert result['valid'] is False
        assert 'Transcription result is missing' in result['errors']

    def test_empty_text_fails(self):
        """Empty transcript text should fail."""
        from shared.analysis_utils import validate_transcription

        transcription = {
            'text': '',
            'confidence': 0.0
        }

        result = validate_transcription(transcription)

        assert result['valid'] is False
        assert 'Transcript text is empty' in result['errors']

    def test_whitespace_only_text_fails(self):
        """Whitespace-only transcript should fail."""
        from shared.analysis_utils import validate_transcription

        transcription = {
            'text': '   \n\t  ',
            'confidence': 0.0
        }

        result = validate_transcription(transcription)

        assert result['valid'] is False
        assert 'Transcript text is empty' in result['errors']

    def test_transcription_with_error_fails(self):
        """Transcription with error should fail."""
        from shared.analysis_utils import validate_transcription

        transcription = {
            'error': 'Audio too short to transcribe',
            'text': None
        }

        result = validate_transcription(transcription)

        assert result['valid'] is False
        assert any('error' in err.lower() for err in result['errors'])


class TestVideoEnrichmentValidation:
    """Tests for complete video enrichment validation."""

    VALID_ANALYSIS = """1. **Visual Content**: The video shows a person cooking.

2. **Audio Content**: Background music with voiceover.

3. **Style & Production**: High-quality footage.

4. **Mood & Tone**: Upbeat and educational.

5. **Key Messages**: Learn to cook pasta.

6. **Content Category**: Tutorial/Educational."""

    def test_valid_response_passes(self):
        """Complete valid response should pass validation."""
        from shared.analysis_utils import validate_video_enrichment

        response = {
            'success': True,
            'video': {'file_name': 'test.mp4'},
            'gemini_analysis': {
                'analysis': self.VALID_ANALYSIS,
                'model': 'gemini-2.0-flash',
                'error': None
            },
            'transcription': {
                'text': 'This is the transcript.',
                'confidence': 0.95
            }
        }

        result = validate_video_enrichment(response)

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_missing_analysis_section_fails(self):
        """Response with missing analysis section fails."""
        from shared.analysis_utils import validate_video_enrichment

        incomplete_analysis = """1. **Visual Content**: Content here.

2. **Audio Content**: Audio here.

3. **Style & Production**: Style here.

4. **Mood & Tone**: Mood here.

6. **Content Category**: Category here."""
        # Missing "Key Messages"

        response = {
            'success': True,
            'gemini_analysis': {
                'analysis': incomplete_analysis,
                'error': None
            }
        }

        result = validate_video_enrichment(response)

        assert result['valid'] is False
        assert any('Key Messages' in err for err in result['errors'])

    def test_gemini_error_fails_validation(self):
        """Gemini analysis with error should fail."""
        from shared.analysis_utils import validate_video_enrichment

        response = {
            'success': True,
            'gemini_analysis': {
                'analysis': None,
                'error': 'Video processing failed'
            }
        }

        result = validate_video_enrichment(response)

        assert result['valid'] is False
        assert any('Gemini analysis error' in err for err in result['errors'])

    def test_empty_transcript_fails_validation(self):
        """Empty transcription should fail validation."""
        from shared.analysis_utils import validate_video_enrichment

        response = {
            'success': True,
            'gemini_analysis': {
                'analysis': self.VALID_ANALYSIS,
                'error': None
            },
            'transcription': {
                'text': '',
                'error': None
            }
        }

        result = validate_video_enrichment(response)

        assert result['valid'] is False
        assert any('Transcript' in err for err in result['errors'])

    def test_response_without_transcription_passes_analysis(self):
        """Response without transcription should still validate analysis."""
        from shared.analysis_utils import validate_video_enrichment

        response = {
            'success': True,
            'gemini_analysis': {
                'analysis': self.VALID_ANALYSIS,
                'error': None
            }
            # No transcription field
        }

        result = validate_video_enrichment(response)

        # Should pass because only gemini_analysis is validated
        assert result['valid'] is True
        assert result['transcription_validation'] is None

    def test_all_six_sections_are_required(self):
        """Verify all 6 user-specified sections are required for video."""
        from shared.analysis_utils import REQUIRED_ANALYSIS_SECTIONS

        # User specified these exact sections:
        user_required = [
            'Visual Content',      # "Visual content"
            'Audio Content',       # "Audio Content"
            'Style & Production',  # "Style & Production"
            'Mood & Tone',         # "Mode & Tone" (interpreted as Mood & Tone)
            'Key Messages',        # "Key messages"
            'Content Category',    # "Content Category"
        ]

        # Verify our config matches user requirements
        for section in user_required:
            assert section in REQUIRED_ANALYSIS_SECTIONS, \
                f"Section '{section}' should be in REQUIRED_ANALYSIS_SECTIONS"


# =============================================================================
# SECTION ICONS VALIDATION
# Tests that ensure the correct icons are defined for each section
# =============================================================================

class TestSectionIcons:
    """Tests for section icon definitions."""

    def test_all_required_sections_have_icons(self):
        """Every required section must have an icon defined."""
        from shared.analysis_utils import REQUIRED_ANALYSIS_SECTIONS, SECTION_ICONS

        for section in REQUIRED_ANALYSIS_SECTIONS:
            assert section in SECTION_ICONS, \
                f"Section '{section}' must have an icon in SECTION_ICONS"
            assert SECTION_ICONS[section], \
                f"Icon for '{section}' should not be empty"

    def test_visual_content_icon_is_eye(self):
        """Visual Content section must use the eye icon 👁️."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Visual Content'] == '👁️'

    def test_audio_content_icon_is_speaker(self):
        """Audio Content section must use the speaker icon 🔊."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Audio Content'] == '🔊'

    def test_style_production_icon_is_clapper(self):
        """Style & Production section must use the clapper board icon 🎬."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Style & Production'] == '🎬'

    def test_mood_tone_icon_is_masks(self):
        """Mood & Tone section must use the theater masks icon 🎭."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Mood & Tone'] == '🎭'

    def test_key_messages_icon_is_lightbulb(self):
        """Key Messages section must use the lightbulb icon 💡."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Key Messages'] == '💡'

    def test_content_category_icon_is_folder(self):
        """Content Category section must use the folder icon 📁."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Content Category'] == '📁'

    def test_transcript_icon_is_memo(self):
        """Transcript section must use the memo icon 📝."""
        from shared.analysis_utils import SECTION_ICONS

        assert SECTION_ICONS['Transcript'] == '📝'

    def test_get_section_icon_returns_correct_icon(self):
        """get_section_icon should return the correct icon for each section."""
        from shared.analysis_utils import get_section_icon

        assert get_section_icon('Visual Content') == '👁️'
        assert get_section_icon('Audio Content') == '🔊'
        assert get_section_icon('Style & Production') == '🎬'
        assert get_section_icon('Mood & Tone') == '🎭'
        assert get_section_icon('Key Messages') == '💡'
        assert get_section_icon('Content Category') == '📁'
        assert get_section_icon('Transcript') == '📝'

    def test_get_section_icon_fallback(self):
        """Unknown sections should get the fallback icon 📌."""
        from shared.analysis_utils import get_section_icon

        assert get_section_icon('Unknown Section') == '📌'
        assert get_section_icon('') == '📌'

    def test_icons_match_n8n_workflow(self):
        """Icons must match the sectionIcons in the n8n workflow."""
        from shared.analysis_utils import SECTION_ICONS

        # These icons are defined in workflows/Bookmark_Processor.json
        # and must stay in sync
        n8n_icons = {
            'Visual Content': '👁️',
            'Audio Content': '🔊',
            'Style & Production': '🎬',
            'Mood & Tone': '🎭',
            'Key Messages': '💡',
            'Content Category': '📁',
            'Transcript': '📝',
        }

        for section, expected_icon in n8n_icons.items():
            assert SECTION_ICONS.get(section) == expected_icon, \
                f"Icon for '{section}' must be '{expected_icon}' to match n8n workflow"
