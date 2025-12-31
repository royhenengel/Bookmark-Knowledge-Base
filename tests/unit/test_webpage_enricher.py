"""
Unit tests for webpage-enricher Cloud Function.

Tests pure functions that don't require external API calls.
"""

import pytest
from bs4 import BeautifulSoup


class TestExtractSpotifyEpisodeId:
    """Tests for extract_spotify_episode_id()"""

    def test_valid_spotify_url(self, extract_spotify_episode_id):
        url = "https://open.spotify.com/episode/1a2b3c4d5e6f7g8h9i0j"
        assert extract_spotify_episode_id(url) == "1a2b3c4d5e6f7g8h9i0j"

    def test_spotify_url_with_query_params(self, extract_spotify_episode_id):
        url = "https://open.spotify.com/episode/abc123XYZ?si=xyz789&utm_source=copy"
        assert extract_spotify_episode_id(url) == "abc123XYZ"

    def test_non_spotify_url(self, extract_spotify_episode_id):
        url = "https://youtube.com/watch?v=abc123"
        assert extract_spotify_episode_id(url) is None

    def test_spotify_album_url(self, extract_spotify_episode_id):
        url = "https://open.spotify.com/album/abc123"
        assert extract_spotify_episode_id(url) is None

    def test_spotify_track_url(self, extract_spotify_episode_id):
        url = "https://open.spotify.com/track/abc123"
        assert extract_spotify_episode_id(url) is None

    def test_empty_url(self, extract_spotify_episode_id):
        assert extract_spotify_episode_id("") is None

    def test_short_spotify_domain(self, extract_spotify_episode_id):
        url = "https://spotify.com/episode/shortID123"
        assert extract_spotify_episode_id(url) == "shortID123"


class TestCalculateReadingTime:
    """Tests for calculate_reading_time()"""

    def test_empty_text(self, calculate_reading_time):
        assert calculate_reading_time("") == 0

    def test_none_text(self, calculate_reading_time):
        assert calculate_reading_time(None) == 0

    def test_short_article_one_minute(self, calculate_reading_time):
        # 225 words = 1 minute at 225 wpm
        text = " ".join(["word"] * 225)
        assert calculate_reading_time(text) == 1

    def test_two_minute_read(self, calculate_reading_time):
        # 450 words = 2 minutes
        text = " ".join(["word"] * 450)
        assert calculate_reading_time(text) == 2

    def test_five_minute_read(self, calculate_reading_time):
        # 1125 words = 5 minutes
        text = " ".join(["word"] * 1125)
        assert calculate_reading_time(text) == 5

    def test_minimum_one_minute(self, calculate_reading_time):
        # Even very short text returns at least 1 minute
        text = "Hello world"
        assert calculate_reading_time(text) == 1

    def test_single_word(self, calculate_reading_time):
        assert calculate_reading_time("hello") == 1


class TestDetectContentType:
    """Tests for detect_content_type()"""

    def test_youtube_url(self, detect_content_type):
        assert detect_content_type("https://www.youtube.com/watch?v=abc123", None) == "video"

    def test_youtu_be_url(self, detect_content_type):
        assert detect_content_type("https://youtu.be/abc123", None) == "video"

    def test_tiktok_url(self, detect_content_type):
        assert detect_content_type("https://www.tiktok.com/@user/video/123", None) == "video"

    def test_vimeo_url(self, detect_content_type):
        assert detect_content_type("https://vimeo.com/12345", None) == "video"

    def test_spotify_podcast(self, detect_content_type):
        assert detect_content_type("https://open.spotify.com/episode/abc123", None) == "podcast"

    def test_apple_podcast(self, detect_content_type):
        assert detect_content_type("https://podcasts.apple.com/us/podcast/episode", None) == "podcast"

    def test_github_url(self, detect_content_type):
        assert detect_content_type("https://github.com/user/repo", None) == "code"

    def test_stackoverflow_url(self, detect_content_type):
        assert detect_content_type("https://stackoverflow.com/questions/123", None) == "code"

    def test_amazon_url(self, detect_content_type):
        assert detect_content_type("https://www.amazon.com/product/B00123", None) == "product"

    def test_amazon_uk_url(self, detect_content_type):
        assert detect_content_type("https://www.amazon.co.uk/dp/B00123", None) == "product"

    def test_twitter_url(self, detect_content_type):
        assert detect_content_type("https://twitter.com/user/status/123", None) == "social"

    def test_x_url(self, detect_content_type):
        assert detect_content_type("https://x.com/user/status/123", None) == "social"

    def test_article_default(self, detect_content_type, sample_article_html):
        result = detect_content_type("https://blog.example.com/post", sample_article_html)
        assert result == "article"

    def test_product_page_by_content(self, detect_content_type, sample_product_html):
        # Generic domain with product content
        result = detect_content_type("https://somestore.com/item", sample_product_html)
        assert result == "product"

    def test_code_page_by_content(self, detect_content_type, sample_code_html):
        # Page with many code blocks detected as code
        result = detect_content_type("https://tutorials.example.com/python", sample_code_html)
        assert result == "code"


class TestExtractMetadata:
    """Tests for extract_metadata()"""

    def test_og_title_extraction(self, extract_metadata, sample_article_html):
        metadata = extract_metadata("https://example.com", sample_article_html)
        assert metadata['title'] == "10 Python Tips You Should Know"

    def test_author_extraction(self, extract_metadata, sample_article_html):
        metadata = extract_metadata("https://example.com", sample_article_html)
        assert metadata['author'] == "Jane Developer"

    def test_image_extraction(self, extract_metadata, sample_article_html):
        metadata = extract_metadata("https://example.com", sample_article_html)
        assert metadata['main_image'] == "https://example.com/image.jpg"

    def test_missing_fields(self, extract_metadata, empty_soup):
        metadata = extract_metadata("https://example.com", empty_soup)
        assert metadata['title'] is None
        assert metadata['author'] is None


class TestExtractPrice:
    """Tests for extract_price()"""

    def test_usd_price(self, extract_price, sample_product_html):
        result = extract_price(sample_product_html)
        assert result['price'] == 29.99
        assert result['currency'] == 'USD'

    def test_no_price(self, extract_price, sample_article_html):
        result = extract_price(sample_article_html)
        assert result['price'] is None
        assert result['currency'] is None

    def test_none_soup(self, extract_price):
        result = extract_price(None)
        assert result['price'] is None
        assert result['currency'] is None

    def test_gbp_price(self, extract_price):
        html = '<html><body><span class="price">£19.99</span></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_price(soup)
        assert result['price'] == 19.99
        assert result['currency'] == 'GBP'

    def test_eur_price(self, extract_price):
        html = '<html><body><span class="price">€49.00</span></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_price(soup)
        assert result['price'] == 49.00
        assert result['currency'] == 'EUR'

    def test_price_with_itemprop(self, extract_price):
        html = '<html><body><span itemprop="price">99.99</span></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_price(soup)
        assert result['price'] == 99.99


class TestExtractCodeSnippets:
    """Tests for extract_code_snippets()"""

    def test_extracts_pre_code_blocks(self, extract_code_snippets, sample_code_html):
        snippets = extract_code_snippets(sample_code_html)
        assert len(snippets) > 0

    def test_empty_soup(self, extract_code_snippets, empty_soup):
        snippets = extract_code_snippets(empty_soup)
        assert snippets == []

    def test_none_soup(self, extract_code_snippets):
        snippets = extract_code_snippets(None)
        assert snippets == []

    def test_no_code_blocks(self, extract_code_snippets, sample_article_html):
        snippets = extract_code_snippets(sample_article_html)
        assert snippets == []
