"""
Shared pytest fixtures for Bookmark Knowledge Base tests.
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from bs4 import BeautifulSoup

# Project root for finding Cloud Function modules
PROJECT_ROOT = Path(__file__).parent.parent


def _load_module_from_path(module_name: str, file_path: Path):
    """Load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load Cloud Function modules with unique names at module load time
_webpage_enricher_module = _load_module_from_path(
    'webpage_enricher_main',
    PROJECT_ROOT / 'webpage-enricher' / 'main.py'
)

_video_enricher_module = _load_module_from_path(
    'video_enricher_main',
    PROJECT_ROOT / 'video-enricher' / 'main.py'
)


# ============================================================================
# Webpage Enricher Function Fixtures
# ============================================================================

@pytest.fixture
def extract_spotify_episode_id():
    """Returns extract_spotify_episode_id function from webpage-enricher."""
    return _webpage_enricher_module.extract_spotify_episode_id


@pytest.fixture
def calculate_reading_time():
    """Returns calculate_reading_time function from webpage-enricher."""
    return _webpage_enricher_module.calculate_reading_time


@pytest.fixture
def detect_content_type():
    """Returns detect_content_type function from webpage-enricher."""
    return _webpage_enricher_module.detect_content_type


@pytest.fixture
def extract_metadata():
    """Returns extract_metadata function from webpage-enricher."""
    return _webpage_enricher_module.extract_metadata


@pytest.fixture
def extract_price():
    """Returns extract_price function from webpage-enricher."""
    return _webpage_enricher_module.extract_price


@pytest.fixture
def extract_code_snippets():
    """Returns extract_code_snippets function from webpage-enricher."""
    return _webpage_enricher_module.extract_code_snippets


# ============================================================================
# Video Enricher Function Fixtures
# ============================================================================

@pytest.fixture
def is_spotify_podcast():
    """Returns is_spotify_podcast function from video-enricher."""
    return _video_enricher_module.is_spotify_podcast


@pytest.fixture
def generate_smart_filename():
    """Returns generate_smart_filename function from video-enricher."""
    return _video_enricher_module.generate_smart_filename


@pytest.fixture
def sample_article_html():
    """Returns BeautifulSoup of a sample article page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>10 Python Tips | Example Blog</title>
        <meta property="og:title" content="10 Python Tips You Should Know">
        <meta name="author" content="Jane Developer">
        <meta property="article:published_time" content="2024-12-15T10:00:00Z">
        <meta property="og:image" content="https://example.com/image.jpg">
        <meta name="description" content="Learn essential Python tips">
    </head>
    <body>
        <article>
            <h1>10 Python Tips You Should Know</h1>
            <p>Here are some tips for Python development.</p>
        </article>
    </body>
    </html>
    """
    return BeautifulSoup(html, 'html.parser')


@pytest.fixture
def sample_product_html():
    """Returns BeautifulSoup of a sample product page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Widget Pro - Best Widgets</title>
    </head>
    <body>
        <div class="product">
            <h1>Widget Pro</h1>
            <span class="price">$29.99</span>
            <button>Add to Cart</button>
        </div>
    </body>
    </html>
    """
    return BeautifulSoup(html, 'html.parser')


@pytest.fixture
def sample_code_html():
    """Returns BeautifulSoup of a page with code snippets."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Python Tutorial</title></head>
    <body>
        <article>
            <h1>How to use Python</h1>
            <pre><code class="language-python">def hello():
    print("Hello, World!")
</code></pre>
            <pre><code>x = 1 + 2</code></pre>
            <pre><code>for i in range(10):
    print(i)
</code></pre>
            <pre><code>import os</code></pre>
        </article>
    </body>
    </html>
    """
    return BeautifulSoup(html, 'html.parser')


@pytest.fixture
def empty_soup():
    """Returns empty BeautifulSoup."""
    return BeautifulSoup("", 'html.parser')


@pytest.fixture
def mock_flask_request():
    """Factory for creating mock Flask request objects."""
    class MockRequest:
        def __init__(self, json_data=None, method='POST'):
            self._json = json_data or {}
            self.method = method
            self.data = b''

        def get_json(self, force=False, silent=False):
            return self._json

    return MockRequest


@pytest.fixture
def spotify_api_response():
    """Sample Spotify Web API response for an episode."""
    return {
        "name": "The Future of AI",
        "description": "In this episode, we discuss the future of AI...",
        "duration_ms": 3600000,
        "release_date": "2024-12-15",
        "images": [{"url": "https://example.com/cover.jpg"}],
        "language": "en",
        "explicit": False,
        "show": {
            "name": "Tech Talk Podcast",
            "description": "Weekly discussions about technology",
            "publisher": "Tech Media Inc",
            "total_episodes": 150
        }
    }


# ============================================================================
# Integration Test Fixtures (HTTP functions)
# ============================================================================

@pytest.fixture
def fetch_webpage():
    """Returns fetch_webpage function from webpage-enricher."""
    return _webpage_enricher_module.fetch_webpage


@pytest.fixture
def get_spotify_access_token():
    """Returns get_spotify_access_token function from webpage-enricher."""
    return _webpage_enricher_module.get_spotify_access_token


@pytest.fixture
def fetch_spotify_episode():
    """Returns fetch_spotify_episode function from webpage-enricher."""
    return _webpage_enricher_module.fetch_spotify_episode


@pytest.fixture
def enrich_webpage():
    """Returns main entry point from webpage-enricher."""
    return _webpage_enricher_module.enrich_webpage


@pytest.fixture
def enrich_video():
    """Returns main entry point from video-enricher."""
    return _video_enricher_module.enrich_video
