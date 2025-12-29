"""
Webpage Enricher Cloud Function

Fetches webpages and extracts enriched metadata for the Bookmark Knowledge Base.

Responsibilities (per ARCHITECTURE.md):
- Fetch webpage content
- Extract metadata (title, author, publish date)
- Calculate reading time
- Detect content type
- Generate AI summary and analysis
- Extract price if product page
- Extract code snippets if dev resource

Does NOT:
- Write to Notion/Raindrop (n8n's job)
- Handle retries (n8n's job)
- Make routing decisions (n8n's job)
"""

import functions_framework
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import json
import os
import google.generativeai as genai
from datetime import datetime

# Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Spotify API token cache
_spotify_token_cache = {'token': None, 'expires_at': 0}

# URL patterns for type detection
VIDEO_PATTERNS = ['youtube.com', 'youtu.be', 'vimeo.com', 'tiktok.com', 'twitch.tv']
SOCIAL_PATTERNS = ['twitter.com', 'x.com', 'instagram.com', 'linkedin.com/posts', 'facebook.com', 'threads.net']
CODE_PATTERNS = ['github.com', 'gitlab.com', 'stackoverflow.com', 'codepen.io', 'jsfiddle.net', 'replit.com']
PRODUCT_PATTERNS = ['amazon.', 'ebay.', 'etsy.com', 'shopify.', 'aliexpress.', 'walmart.com', 'target.com']
PODCAST_PATTERNS = ['spotify.com/episode', 'podcasts.apple.com', 'overcast.fm', 'pocketcasts.com']


def get_spotify_access_token() -> str:
    """Get Spotify API access token using Client Credentials flow."""
    import time

    # Check cache first
    if _spotify_token_cache['token'] and time.time() < _spotify_token_cache['expires_at']:
        return _spotify_token_cache['token']

    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None

    try:
        import base64
        auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

        response = requests.post(
            'https://accounts.spotify.com/api/token',
            headers={
                'Authorization': f'Basic {auth_bytes}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={'grant_type': 'client_credentials'},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Cache the token (expires_in is typically 3600 seconds)
        _spotify_token_cache['token'] = data['access_token']
        _spotify_token_cache['expires_at'] = time.time() + data.get('expires_in', 3600) - 60  # 60s buffer

        return data['access_token']
    except Exception as e:
        print(f"Spotify auth error: {e}")
        return None


def extract_spotify_episode_id(url: str) -> str:
    """Extract episode ID from Spotify URL."""
    import re
    # Matches: open.spotify.com/episode/XXXXXX or spotify.com/episode/XXXXXX
    match = re.search(r'spotify\.com/episode/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None


def fetch_spotify_episode(url: str) -> dict:
    """Fetch rich metadata from Spotify Web API for podcast episodes."""
    episode_id = extract_spotify_episode_id(url)
    if not episode_id:
        return {'success': False, 'error': 'Could not extract episode ID from URL'}

    token = get_spotify_access_token()
    if not token:
        # Fall back to oEmbed if no API credentials
        return fetch_spotify_oembed(url)

    try:
        response = requests.get(
            f'https://api.spotify.com/v1/episodes/{episode_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        # Extract show info
        show = data.get('show', {})

        # Format duration (ms to minutes)
        duration_ms = data.get('duration_ms', 0)
        duration_minutes = round(duration_ms / 60000) if duration_ms else None

        return {
            'success': True,
            'title': data.get('name'),
            'description': data.get('description') or data.get('html_description'),
            'thumbnail_url': data.get('images', [{}])[0].get('url') if data.get('images') else None,
            'release_date': data.get('release_date'),
            'duration_minutes': duration_minutes,
            'show_name': show.get('name'),
            'show_description': show.get('description'),
            'publisher': show.get('publisher'),
            'total_episodes': show.get('total_episodes'),
            'explicit': data.get('explicit', False),
            'language': data.get('language'),
            'type': 'podcast',
            'provider_name': 'Spotify'
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {'success': False, 'error': 'Episode not found'}
        return {'success': False, 'error': f'Spotify API error: {e.response.status_code}'}
    except Exception as e:
        # Fall back to oEmbed on any error
        print(f"Spotify API error, falling back to oEmbed: {e}")
        return fetch_spotify_oembed(url)


def fetch_spotify_oembed(url: str) -> dict:
    """Fetch metadata from Spotify oEmbed API for podcast episodes (fallback)."""
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        response = requests.get(oembed_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            'title': data.get('title'),
            'thumbnail_url': data.get('thumbnail_url'),
            'provider_name': data.get('provider_name', 'Spotify'),
            'type': 'podcast',
            'success': True
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def search_podcast_itunes(show_name: str) -> dict:
    """Search for a podcast's RSS feed using the iTunes Search API."""
    try:
        # Clean up show name for search
        search_term = show_name.replace("'", "").replace('"', '')

        response = requests.get(
            'https://itunes.apple.com/search',
            params={
                'term': search_term,
                'media': 'podcast',
                'limit': 5
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])
        if not results:
            return {'success': False, 'error': 'No podcasts found'}

        # Find best match - prefer exact name match
        best_match = None
        for result in results:
            if result.get('collectionName', '').lower() == show_name.lower():
                best_match = result
                break

        # Fall back to first result
        if not best_match:
            best_match = results[0]

        return {
            'success': True,
            'rss_url': best_match.get('feedUrl'),
            'podcast_name': best_match.get('collectionName'),
            'artist_name': best_match.get('artistName'),
            'artwork_url': best_match.get('artworkUrl600')
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def find_episode_in_rss(rss_url: str, episode_title: str, duration_minutes: int = None) -> dict:
    """Find a specific episode in an RSS feed and return its audio URL."""
    import feedparser
    from difflib import SequenceMatcher

    try:
        # Parse RSS feed
        feed = feedparser.parse(rss_url)

        if not feed.entries:
            return {'success': False, 'error': 'No episodes found in RSS feed'}

        # Normalize search title
        search_title = episode_title.lower().strip()

        best_match = None
        best_score = 0

        for entry in feed.entries:
            entry_title = entry.get('title', '').lower().strip()

            # Calculate similarity score
            score = SequenceMatcher(None, search_title, entry_title).ratio()

            # Boost score if duration matches (within 2 minutes)
            if duration_minutes:
                entry_duration = None
                # Try to get duration from itunes:duration
                if hasattr(entry, 'itunes_duration'):
                    dur = entry.itunes_duration
                    if ':' in str(dur):
                        parts = str(dur).split(':')
                        if len(parts) == 2:
                            entry_duration = int(parts[0])
                        elif len(parts) == 3:
                            entry_duration = int(parts[0]) * 60 + int(parts[1])
                    else:
                        try:
                            entry_duration = int(dur) // 60
                        except:
                            pass

                if entry_duration and abs(entry_duration - duration_minutes) <= 2:
                    score += 0.2  # Boost for matching duration

            if score > best_score:
                best_score = score
                best_match = entry

        # Require at least 50% match
        if best_score < 0.5:
            return {'success': False, 'error': f'No matching episode found (best score: {best_score:.2f})'}

        # Extract audio URL from enclosures
        audio_url = None
        if best_match.get('enclosures'):
            for enc in best_match.enclosures:
                if enc.get('type', '').startswith('audio/'):
                    audio_url = enc.get('href') or enc.get('url')
                    break

        # Fallback to links
        if not audio_url and best_match.get('links'):
            for link in best_match.links:
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break

        if not audio_url:
            return {'success': False, 'error': 'No audio URL found in episode'}

        return {
            'success': True,
            'audio_url': audio_url,
            'episode_title': best_match.get('title'),
            'match_score': best_score
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def transcribe_audio_url(audio_url: str) -> dict:
    """Transcribe audio from URL using AssemblyAI."""
    if not ASSEMBLYAI_API_KEY:
        return {'success': False, 'error': 'ASSEMBLYAI_API_KEY not configured'}

    try:
        import assemblyai as aai

        aai.settings.api_key = ASSEMBLYAI_API_KEY

        # Configure transcription
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            punctuate=True,
            format_text=True,
        )

        # Create transcriber and transcribe
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_url)

        if transcript.status == aai.TranscriptStatus.error:
            return {'success': False, 'error': transcript.error}

        return {
            'success': True,
            'text': transcript.text,
            'confidence': transcript.confidence,
            'audio_duration_seconds': transcript.audio_duration
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def detect_content_type(url: str, soup: BeautifulSoup) -> str:
    """Detect the type of content based on URL and page content."""
    domain = urlparse(url).netloc.lower()

    # Check URL patterns first
    for pattern in VIDEO_PATTERNS:
        if pattern in domain:
            return 'video'

    for pattern in PODCAST_PATTERNS:
        if pattern in url.lower():
            return 'podcast'

    for pattern in SOCIAL_PATTERNS:
        if pattern in domain:
            return 'social'

    for pattern in CODE_PATTERNS:
        if pattern in domain:
            return 'code'

    for pattern in PRODUCT_PATTERNS:
        if pattern in domain:
            return 'product'

    # Check page content for product indicators
    if soup:
        # Look for price indicators
        price_patterns = soup.find_all(attrs={'class': re.compile(r'price|cost|amount', re.I)})
        add_to_cart = soup.find_all(text=re.compile(r'add to cart|buy now|purchase', re.I))
        if price_patterns or add_to_cart:
            return 'product'

        # Look for code blocks
        code_blocks = soup.find_all(['pre', 'code'])
        if len(code_blocks) > 3:
            return 'code'

    return 'article'


def extract_metadata(url: str, soup: BeautifulSoup) -> dict:
    """Extract metadata from the webpage."""
    metadata = {
        'title': None,
        'author': None,
        'published_date': None,
        'main_image': None,
        'description': None,
    }

    if not soup:
        return metadata

    # Title - try multiple sources
    og_title = soup.find('meta', property='og:title')
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    title_tag = soup.find('title')
    h1_tag = soup.find('h1')

    metadata['title'] = (
        og_title.get('content') if og_title else
        twitter_title.get('content') if twitter_title else
        title_tag.get_text(strip=True) if title_tag else
        h1_tag.get_text(strip=True) if h1_tag else
        None
    )

    # Author
    author_meta = soup.find('meta', attrs={'name': 'author'})
    author_prop = soup.find('meta', property='article:author')
    author_rel = soup.find('a', rel='author')
    author_class = soup.find(attrs={'class': re.compile(r'author|byline', re.I)})

    metadata['author'] = (
        author_meta.get('content') if author_meta else
        author_prop.get('content') if author_prop else
        author_rel.get_text(strip=True) if author_rel else
        author_class.get_text(strip=True) if author_class else
        None
    )

    # Clean up author if found
    if metadata['author']:
        metadata['author'] = re.sub(r'^by\s+', '', metadata['author'], flags=re.I).strip()

    # Published date
    date_meta = soup.find('meta', property='article:published_time')
    date_time = soup.find('time', attrs={'datetime': True})

    date_str = (
        date_meta.get('content') if date_meta else
        date_time.get('datetime') if date_time else
        None
    )

    if date_str:
        try:
            # Parse ISO format
            metadata['published_date'] = date_str[:10]  # Just YYYY-MM-DD
        except:
            pass

    # Main image
    og_image = soup.find('meta', property='og:image')
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})

    metadata['main_image'] = (
        og_image.get('content') if og_image else
        twitter_image.get('content') if twitter_image else
        None
    )

    # Description
    og_desc = soup.find('meta', property='og:description')
    meta_desc = soup.find('meta', attrs={'name': 'description'})

    metadata['description'] = (
        og_desc.get('content') if og_desc else
        meta_desc.get('content') if meta_desc else
        None
    )

    return metadata


def extract_main_content(soup: BeautifulSoup) -> str:
    """Extract the main text content from the page."""
    if not soup:
        return ""

    # Remove script, style, nav, footer, header elements
    for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
        element.decompose()

    # Try to find main content area
    main_content = (
        soup.find('article') or
        soup.find('main') or
        soup.find(attrs={'class': re.compile(r'content|post|article|entry', re.I)}) or
        soup.find('body')
    )

    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text[:15000]  # Limit to ~15k chars for AI processing

    return ""


def calculate_reading_time(text: str) -> int:
    """Calculate estimated reading time in minutes."""
    if not text:
        return 0

    # Average reading speed: 200-250 words per minute
    word_count = len(text.split())
    reading_time = max(1, round(word_count / 225))
    return reading_time


def extract_price(soup: BeautifulSoup) -> dict:
    """Extract price information from product pages."""
    result = {'price': None, 'currency': None}

    if not soup:
        return result

    # Common price patterns
    price_selectors = [
        {'class': re.compile(r'price', re.I)},
        {'itemprop': 'price'},
        {'data-price': True},
    ]

    for selector in price_selectors:
        element = soup.find(attrs=selector)
        if element:
            text = element.get_text(strip=True)
            # Extract price with regex
            match = re.search(r'[\$\£\€]?\s*(\d+(?:[.,]\d{2})?)', text)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    result['price'] = float(price_str)
                except:
                    pass

                # Detect currency
                if '$' in text:
                    result['currency'] = 'USD'
                elif '£' in text:
                    result['currency'] = 'GBP'
                elif '€' in text:
                    result['currency'] = 'EUR'

                break

    return result


def extract_code_snippets(soup: BeautifulSoup) -> list:
    """Extract code snippets from the page."""
    snippets = []

    if not soup:
        return snippets

    # Find code blocks
    code_blocks = soup.find_all(['pre', 'code'])

    for block in code_blocks:
        code = block.get_text(strip=True)
        if len(code) > 20 and len(code) < 5000:  # Reasonable code block size
            # Detect language from class
            classes = block.get('class', [])
            language = None
            for cls in classes:
                if 'language-' in cls:
                    language = cls.replace('language-', '')
                    break

            snippets.append({
                'code': code[:2000],  # Limit size
                'language': language
            })

    return snippets[:5]  # Max 5 snippets


def generate_ai_analysis(url: str, title: str, content: str, content_type: str) -> dict:
    """Generate AI-cleaned title, summary and analysis using Gemini."""
    result = {
        'title': title,  # Fallback to original
        'summary': None,
        'analysis': None,
        'error': None
    }

    if not GEMINI_API_KEY:
        result['error'] = 'GEMINI_API_KEY not configured'
        return result

    if not content or len(content) < 100:
        result['error'] = 'Insufficient content for analysis'
        return result

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = f"""Analyze this webpage and provide:

1. **Title**: Clean up the raw title. Keep it as close to the original as possible but:
   - Remove site names, separators like " | " or " - Site Name" at the end
   - Keep it under 100 characters
   - Make it descriptive and recognizable
   - If the title includes a long description after ":" or "-", keep only the main title part

2. **Summary**: A 2-3 sentence summary of what this page is about.

3. **Analysis**: Why might someone save this bookmark? What are the key takeaways or value? Who would find this useful?

URL: {url}
Raw Title: {title}
Content Type: {content_type}

Page Content:
{content[:10000]}

Respond in this exact JSON format:
{{
  "title": "Cleaned title here (max 100 chars)",
  "summary": "2-3 sentence summary here",
  "analysis": "Why this is useful, key takeaways, target audience"
}}
"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            result['title'] = parsed.get('title') or title
            result['summary'] = parsed.get('summary')
            result['analysis'] = parsed.get('analysis')
        else:
            # Fallback: use whole response as analysis
            result['analysis'] = response_text

    except Exception as e:
        result['error'] = str(e)

    return result


def fetch_webpage(url: str) -> tuple:
    """Fetch webpage content. Returns (html, error)."""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()

        return response.text, None

    except requests.exceptions.Timeout:
        return None, 'Request timed out'
    except requests.exceptions.HTTPError as e:
        return None, f'HTTP error: {e.response.status_code}'
    except requests.exceptions.RequestException as e:
        return None, f'Request failed: {str(e)}'


@functions_framework.http
def enrich_webpage(request):
    """
    Main Cloud Function entry point.

    Expected JSON input:
    {
        "url": "https://example.com/article",
        "options": {
            "skip_ai": false,
            "extract_code": true
        }
    }
    """
    # Handle CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        request_json = request.get_json(silent=True)

        if not request_json or 'url' not in request_json:
            return (json.dumps({
                'error': 'Missing required field: url'
            }), 400, headers)

        url = request_json['url']
        options = request_json.get('options', {})
        skip_ai = options.get('skip_ai', False)
        extract_code = options.get('extract_code', True)

        # Extract domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')

        # Special handling for Spotify podcast episodes - use Web API (with oEmbed fallback)
        if 'spotify.com/episode' in url.lower():
            spotify_data = fetch_spotify_episode(url)
            if spotify_data.get('success'):
                # Build content for AI analysis - much richer with Web API data
                content_parts = []
                if spotify_data.get('title'):
                    content_parts.append(f"Episode: {spotify_data['title']}")
                if spotify_data.get('show_name'):
                    content_parts.append(f"Show: {spotify_data['show_name']}")
                if spotify_data.get('publisher'):
                    content_parts.append(f"Publisher: {spotify_data['publisher']}")
                if spotify_data.get('description'):
                    content_parts.append(f"Description: {spotify_data['description']}")
                if spotify_data.get('show_description'):
                    content_parts.append(f"Show Description: {spotify_data['show_description']}")
                if spotify_data.get('duration_minutes'):
                    content_parts.append(f"Duration: {spotify_data['duration_minutes']} minutes")

                content_for_ai = '\n'.join(content_parts)

                # Generate AI analysis with rich content
                ai_result = {'title': spotify_data['title'], 'summary': None, 'analysis': None}
                if not options.get('skip_ai', False) and GEMINI_API_KEY and content_for_ai:
                    try:
                        genai.configure(api_key=GEMINI_API_KEY)
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        prompt = f"""Analyze this podcast episode:

{content_for_ai}

Platform: Spotify

Provide:
1. A 2-3 sentence summary of what this episode covers
2. Key topics and who would find this useful

Respond in this exact JSON format (both values must be plain text strings, not arrays or objects):
{{"summary": "Your 2-3 sentence summary here", "analysis": "Key topics: topic1, topic2, topic3. Target audience: description of who would find this useful."}}"""
                        response = model.generate_content(prompt)
                        json_match = re.search(r'\{[\s\S]*\}', response.text.strip())
                        if json_match:
                            parsed = json.loads(json_match.group())
                            ai_result['summary'] = parsed.get('summary')
                            # Ensure analysis is a string
                            analysis = parsed.get('analysis')
                            if isinstance(analysis, dict):
                                parts = []
                                if 'key_topics' in analysis:
                                    parts.append(f"Key topics: {', '.join(analysis['key_topics']) if isinstance(analysis['key_topics'], list) else analysis['key_topics']}")
                                if 'target_audience' in analysis:
                                    parts.append(f"Target audience: {', '.join(analysis['target_audience']) if isinstance(analysis['target_audience'], list) else analysis['target_audience']}")
                                analysis = '. '.join(parts) if parts else str(analysis)
                            ai_result['analysis'] = analysis
                    except Exception as e:
                        ai_result['error'] = str(e)

                # Use show name + publisher as author if available
                author = spotify_data.get('publisher') or spotify_data.get('show_name') or spotify_data.get('provider_name', 'Spotify')

                # Try to get transcription via RSS feed
                transcription = None
                transcription_error = None

                if spotify_data.get('show_name') and spotify_data.get('title'):
                    # Step 1: Find RSS feed via iTunes
                    rss_result = search_podcast_itunes(spotify_data['show_name'])

                    if rss_result.get('success') and rss_result.get('rss_url'):
                        # Step 2: Find episode in RSS
                        episode_result = find_episode_in_rss(
                            rss_result['rss_url'],
                            spotify_data['title'],
                            spotify_data.get('duration_minutes')
                        )

                        if episode_result.get('success') and episode_result.get('audio_url'):
                            # Step 3: Transcribe audio
                            transcription_result = transcribe_audio_url(episode_result['audio_url'])

                            if transcription_result.get('success'):
                                transcription = transcription_result.get('text')
                            else:
                                transcription_error = f"Transcription failed: {transcription_result.get('error')}"
                        else:
                            transcription_error = f"Episode not found in RSS: {episode_result.get('error')}"
                    else:
                        transcription_error = f"RSS feed not found: {rss_result.get('error')}"

                response_data = {
                    'url': url,
                    'domain': domain,
                    'type': 'podcast',
                    'title': spotify_data['title'],
                    'author': author,
                    'published_date': spotify_data.get('release_date'),
                    'main_image': spotify_data.get('thumbnail_url'),
                    'description': spotify_data.get('description'),
                    'reading_time': spotify_data.get('duration_minutes'),  # Use duration as "reading time" for podcasts
                    'price': None,
                    'currency': None,
                    'code_snippets': [],
                    'ai_summary': ai_result.get('summary'),
                    'ai_analysis': ai_result.get('analysis'),
                    'processed_at': datetime.utcnow().isoformat() + 'Z',
                    # Extra Spotify-specific fields
                    'show_name': spotify_data.get('show_name'),
                    'show_description': spotify_data.get('show_description'),
                    'episode_duration_minutes': spotify_data.get('duration_minutes'),
                    # Transcription
                    'transcription': transcription,
                }

                # Collect errors
                errors = []
                if ai_result.get('error'):
                    errors.append({'stage': 'ai_analysis', 'message': ai_result['error'], 'recoverable': True})
                if transcription_error:
                    errors.append({'stage': 'transcription', 'message': transcription_error, 'recoverable': True})

                if errors:
                    response_data['errors'] = errors

                return (json.dumps(response_data), 200, headers)

        # Fetch the webpage
        html, fetch_error = fetch_webpage(url)

        if fetch_error:
            return (json.dumps({
                'url': url,
                'domain': domain,
                'error': {
                    'stage': 'fetch',
                    'message': fetch_error,
                    'recoverable': True
                }
            }), 200, headers)  # Return 200 with error in body per ARCHITECTURE.md

        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Detect content type
        content_type = detect_content_type(url, soup)

        # Extract metadata
        metadata = extract_metadata(url, soup)

        # Extract main content
        main_content = extract_main_content(soup)

        # Calculate reading time
        reading_time = calculate_reading_time(main_content) if content_type == 'article' else None

        # Extract price if product
        price_info = extract_price(soup) if content_type == 'product' else {'price': None, 'currency': None}

        # Extract code snippets if code resource
        code_snippets = extract_code_snippets(soup) if (content_type == 'code' and extract_code) else []

        # Generate AI analysis (includes cleaned title)
        ai_result = {'title': metadata['title'], 'summary': None, 'analysis': None, 'error': None}
        if not skip_ai:
            ai_result = generate_ai_analysis(url, metadata['title'], main_content, content_type)

        # Build response - use AI-cleaned title
        response = {
            'url': url,
            'domain': domain,
            'type': content_type,
            'title': ai_result.get('title') or metadata['title'],
            'author': metadata['author'],
            'published_date': metadata['published_date'],
            'main_image': metadata['main_image'],
            'description': metadata['description'],
            'reading_time': reading_time,
            'price': price_info['price'],
            'currency': price_info['currency'],
            'code_snippets': code_snippets,
            'ai_summary': ai_result['summary'],
            'ai_analysis': ai_result['analysis'],
            'processed_at': datetime.utcnow().isoformat() + 'Z',
        }

        # Include errors if any (partial success per ARCHITECTURE.md)
        if ai_result.get('error'):
            response['error'] = {
                'stage': 'ai_analysis',
                'message': ai_result['error'],
                'recoverable': True
            }

        return (json.dumps(response), 200, headers)

    except Exception as e:
        return (json.dumps({
            'error': {
                'stage': 'processing',
                'message': str(e),
                'recoverable': False
            }
        }), 500, headers)
