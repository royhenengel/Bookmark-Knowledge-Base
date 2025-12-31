import functions_framework
from google.oauth2 import service_account
from google.cloud import storage
import google.generativeai as genai
import assemblyai as aai
import yt_dlp
import tempfile
import subprocess
import os
import sys
import json
import traceback
import time
from datetime import timedelta

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.title_utils import truncate_title, validate_title, sanitize_title, MAX_TITLE_LENGTH
from shared.analysis_utils import validate_video_enrichment, REQUIRED_ANALYSIS_SECTIONS, SECTION_ICONS

# Configuration
BUCKET_NAME = os.environ.get('GCS_BUCKET', 'video-processor-temp-rhe')
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')  # Required: set via Cloud Function environment variable
ASSEMBLYAI_API_KEY = os.environ.get('ASSEMBLYAI_API_KEY')  # Required for transcription


def get_storage_client():
    """Initialize Cloud Storage client."""
    creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )
        return storage.Client(credentials=creds, project=creds_dict.get('project_id'))
    else:
        # Use default credentials in Cloud Functions
        return storage.Client()


def is_spotify_podcast(url):
    """Check if URL is a Spotify podcast episode."""
    return 'spotify.com/episode' in url.lower()


def get_spotify_metadata(url):
    """Get podcast metadata from Spotify oEmbed API."""
    import requests
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        response = requests.get(oembed_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            'title': data.get('title', 'Unknown Episode'),
            'thumbnail': data.get('thumbnail_url'),
            'provider': data.get('provider_name', 'Spotify'),
            'success': True
        }
    except Exception as e:
        print(f"Spotify oEmbed error: {e}")
        return {'success': False, 'error': str(e)}


def search_youtube_with_api(query, max_results=5):
    """Search YouTube using the YouTube Data API (falls back from yt-dlp)."""
    import requests

    api_key = os.environ.get('GEMINI_API_KEY')  # Try Google API key
    if not api_key:
        return None

    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': api_key,
            'videoDuration': 'long',  # Filter for videos > 20 min (podcasts)
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            if items:
                video_id = items[0]['id']['videoId']
                title = items[0]['snippet']['title']
                print(f"YouTube API found: {title}")
                return f"https://youtube.com/watch?v={video_id}"
        else:
            print(f"YouTube API error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"YouTube API search failed: {e}")
    return None


def search_youtube_for_podcast(episode_title, show_name=None, max_results=10):
    """Search YouTube for a podcast episode by title.

    Returns the best matching YouTube URL or None if not found.
    """
    try:
        print(f"Searching YouTube for: {episode_title}")

        # Clean up title for better search
        search_query = episode_title
        # Remove common podcast prefixes
        for prefix in ['Most Replayed Moment:', 'Ep.', 'Episode', '#']:
            if search_query.startswith(prefix):
                search_query = search_query[len(prefix):].strip()

        # Add show name to improve search if available
        if show_name and show_name not in search_query:
            search_query = f"{show_name} {search_query}"

        print(f"Search query: {search_query}")

        # Try YouTube Data API first (more reliable in cloud)
        api_result = search_youtube_with_api(search_query)
        if api_result:
            return api_result

        # Fallback to yt-dlp search
        print("Trying yt-dlp search fallback...")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': f'ytsearch{max_results}',
            # Use same anti-bot measures as download
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android_vr', 'tv_embedded'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)

            if results and results.get('entries'):
                entries = results['entries']
                print(f"Found {len(entries)} YouTube results")

                # Return first result that looks like it could be the podcast
                for entry in entries:
                    if entry and entry.get('id'):
                        title = entry.get('title', '')
                        duration = entry.get('duration', 0)

                        # Prefer longer videos (podcasts are usually 10+ minutes)
                        if duration and duration > 300:  # > 5 minutes
                            youtube_url = f"https://youtube.com/watch?v={entry['id']}"
                            print(f"Found matching video: {title} ({duration}s)")
                            return youtube_url

                # Fallback to first result if no long videos found
                first_entry = entries[0]
                if first_entry and first_entry.get('id'):
                    youtube_url = f"https://youtube.com/watch?v={first_entry['id']}"
                    print(f"Using first result: {first_entry.get('title')}")
                    return youtube_url

        print("No YouTube results found")
        return None

    except Exception as e:
        print(f"YouTube search error: {e}")
        return None


def download_spotify_podcast(url, tmpdir):
    """Download Spotify podcast by finding it on YouTube.

    Strategy:
    1. Get episode metadata from Spotify oEmbed
    2. Search YouTube for the episode
    3. Download from YouTube if found
    """
    print(f"Processing Spotify podcast: {url}")

    # Get metadata from Spotify
    spotify_meta = get_spotify_metadata(url)
    if not spotify_meta.get('success'):
        raise Exception(f"Failed to get Spotify metadata: {spotify_meta.get('error')}")

    episode_title = spotify_meta['title']
    show_name = spotify_meta.get('show_name')
    print(f"Episode title: {episode_title}")
    print(f"Show name: {show_name}")

    # Search YouTube for this episode - try with show name first, then without
    youtube_url = search_youtube_for_podcast(episode_title, show_name)

    if not youtube_url:
        # Try searching with just the title
        print("No results with show name, trying title only...")
        youtube_url = search_youtube_for_podcast(episode_title)

    if youtube_url:
        print(f"Found on YouTube: {youtube_url}")
        try:
            # Download from YouTube using existing function
            result = download_with_ytdlp(youtube_url, tmpdir)
            # Override some metadata with Spotify info
            result['source'] = 'spotify_via_youtube'
            result['original_url'] = url
            result['spotify_title'] = episode_title
            result['spotify_thumbnail'] = spotify_meta.get('thumbnail')
            return result
        except Exception as e:
            error_msg = str(e)
            if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
                print(f"YouTube download blocked by bot detection: {e}")
                raise Exception(
                    f"YouTube download blocked by bot detection. "
                    f"Try adding a YOUTUBE_COOKIE_FILE or using a residential proxy. "
                    f"Found video: {youtube_url}"
                )
            raise
    else:
        # YouTube not found - raise error for now
        # TODO: Add Podcast Index RSS fallback here
        raise Exception(f"Could not find '{episode_title}' on YouTube. Podcast Index fallback not yet implemented.")


def download_video(url, tmpdir):
    """Download video - handles TikTok, Spotify podcasts, and other sources."""
    import requests

    # Detect source
    if is_spotify_podcast(url):
        return download_spotify_podcast(url, tmpdir)
    elif 'tiktok' in url.lower():
        return download_tiktok_video(url, tmpdir)
    else:
        return download_with_ytdlp(url, tmpdir)


def download_tiktok_video(url, tmpdir):
    """Download TikTok video using yt-dlp (primary) with RapidAPI fallback."""

    # Try yt-dlp first (free, no API limits)
    try:
        print(f"Attempting TikTok download with yt-dlp: {url}")
        print(f"tmpdir type: {type(tmpdir)}, value: {tmpdir}")
        result = download_tiktok_with_ytdlp(url, tmpdir)
        print("yt-dlp download successful")
        return result
    except Exception as ytdlp_error:
        import traceback
        print(f"yt-dlp failed: {ytdlp_error}")
        print(f"Full traceback: {traceback.format_exc()}")
        print("Falling back to RapidAPI")

    # Fallback to RapidAPI
    return download_tiktok_with_rapidapi(url, tmpdir)


def download_tiktok_with_ytdlp(url, tmpdir):
    """Download TikTok video using yt-dlp."""
    import io

    # Ensure tmpdir is a string (not bytes)
    if isinstance(tmpdir, bytes):
        tmpdir = tmpdir.decode('utf-8')

    output_template = os.path.join(str(tmpdir), '%(id)s.%(ext)s')

    # Create a null logger to avoid stdout/stderr issues in Cloud Functions
    class NullLogger:
        def debug(self, msg): pass
        def info(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): print(f"yt-dlp error: {msg}")

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'logger': NullLogger(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = str(info.get('id', 'unknown'))
        ext = str(info.get('ext', 'mp4'))

        # Use yt-dlp's prepared filename to get actual path
        filepath = ydl.prepare_filename(info)

        # Fallback if prepare_filename doesn't work
        if not os.path.exists(filepath):
            filepath = os.path.join(str(tmpdir), f"{video_id}.{ext}")

        # Get title - TikTok often puts it in description
        title = info.get('title') or ''
        if not title or title == video_id:
            title = info.get('description', 'Untitled')

        # Sanitize and truncate title at word boundary (max 70 chars)
        title = sanitize_title(str(title)) if title else 'Untitled'
        title, was_truncated = truncate_title(title)
        if not title:
            title = 'Untitled'

        return {
            'filepath': filepath,
            'title': title,
            'duration': info.get('duration', 0),
            'ext': ext,
            'uploader': str(info.get('uploader') or info.get('creator') or info.get('uploader_id') or 'Unknown'),
            'video_id': video_id,
            'source': 'tiktok',
            'thumbnail': info.get('thumbnail'),
            'download_method': 'yt-dlp',
        }


def download_tiktok_with_rapidapi(url, tmpdir):
    """Download TikTok video using RapidAPI (fallback method)."""
    import requests

    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '884a3146bfmsh62db44df12afa3ap1128d5jsn232683fd49f1')

    # Get video info from RapidAPI
    api_url = "https://tiktok-video-no-watermark2.p.rapidapi.com"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "tiktok-video-no-watermark2.p.rapidapi.com"
    }
    params = {"url": url, "hd": "1"}

    response = requests.get(api_url, headers=headers, params=params)
    data = response.json()

    if data.get('code') != 0:
        raise Exception(f"RapidAPI error: {data.get('msg', 'Unknown error')}")

    video_data = data.get('data', {})
    video_url = video_data.get('hdplay') or video_data.get('play')

    if not video_url:
        raise Exception("No video URL found in RapidAPI response")

    # Download the video
    video_id = video_data.get('id', 'unknown')
    filepath = os.path.join(tmpdir, f"{video_id}.mp4")

    video_response = requests.get(video_url, stream=True)
    with open(filepath, 'wb') as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("RapidAPI download successful")
    return {
        'filepath': filepath,
        'title': video_data.get('title', 'Untitled'),
        'duration': video_data.get('duration', 0),
        'ext': 'mp4',
        'uploader': video_data.get('author', {}).get('unique_id', 'Unknown'),
        'video_id': video_id,
        'source': 'tiktok',
        'thumbnail': video_data.get('cover'),
        'download_method': 'rapidapi',
    }


def download_with_ytdlp(url, tmpdir):
    """Download video using yt-dlp for non-TikTok sources."""
    output_template = os.path.join(tmpdir, '%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        # Anti-bot measures for YouTube - try multiple clients
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android_vr', 'tv_embedded'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
        },
        'socket_timeout': 60,
        'retries': 3,
        'fragment_retries': 3,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info.get('id', 'unknown')
        ext = info.get('ext', 'mp4')
        filepath = os.path.join(tmpdir, f"{video_id}.{ext}")

        # Detect source
        if 'youtube' in url.lower() or 'youtu.be' in url.lower():
            source = 'youtube'
        else:
            source = 'other'

        return {
            'filepath': filepath,
            'title': info.get('title', 'Untitled'),
            'duration': info.get('duration', 0),
            'ext': ext,
            'uploader': info.get('uploader', 'Unknown'),
            'video_id': video_id,
            'source': source,
            'thumbnail': info.get('thumbnail'),
        }


def extract_audio(video_path, tmpdir):
    """Extract audio from video using ffmpeg."""
    audio_filename = os.path.basename(video_path).rsplit('.', 1)[0] + '.mp3'
    audio_path = os.path.join(tmpdir, audio_filename)

    try:
        subprocess.run([
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
            '-y', audio_path
        ], check=True, capture_output=True)
        return audio_path
    except subprocess.CalledProcessError as e:
        print(f"Audio extraction failed: {e}")
        return None


def transcribe_audio(audio_path, api_key=None):
    """Transcribe audio using AssemblyAI.

    Args:
        audio_path: Path to the audio file (MP3)
        api_key: AssemblyAI API key (optional, uses env var if not provided)

    Returns:
        dict with transcript text, confidence, language, or error
    """
    api_key = api_key or ASSEMBLYAI_API_KEY
    if not api_key:
        return {'error': 'No AssemblyAI API key provided', 'text': None}

    try:
        print(f"Starting audio transcription for: {audio_path}")

        # Configure AssemblyAI
        aai.settings.api_key = api_key

        # Create transcriber with auto language detection
        config = aai.TranscriptionConfig(
            language_detection=True,
            punctuate=True,
            format_text=True,
        )

        transcriber = aai.Transcriber(config=config)

        # Transcribe the audio file
        print("Uploading and transcribing audio...")
        transcript = transcriber.transcribe(audio_path)

        if transcript.status == aai.TranscriptStatus.error:
            return {
                'error': transcript.error,
                'text': None
            }

        print(f"Transcription complete. Length: {len(transcript.text or '')} chars")

        return {
            'text': transcript.text,
            'confidence': getattr(transcript, 'confidence', None),
            'language': getattr(transcript, 'language_code', None) or getattr(transcript, 'language', None),
            'duration_seconds': getattr(transcript, 'audio_duration', None),
            'word_count': len(transcript.words) if hasattr(transcript, 'words') and transcript.words else 0,
            'error': None
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Transcription error: {error_msg}")
        return {
            'error': error_msg,
            'text': None
        }


def upload_to_gcs(client, filepath, filename):
    """Upload file to Cloud Storage and return public URL."""
    bucket = client.bucket(BUCKET_NAME)
    blob_name = f"videos/{filename}"
    blob = bucket.blob(blob_name)

    # Determine content type
    if filepath.endswith('.mp3'):
        content_type = 'audio/mpeg'
    else:
        content_type = 'video/mp4'

    # Upload file
    blob.upload_from_filename(filepath, content_type=content_type)

    # Get file size
    blob.reload()
    size = blob.size

    # Generate public URL (bucket is already public via IAM)
    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        'blob_name': blob_name,
        'public_url': public_url,
        'size_bytes': size
    }


def generate_smart_filename(title, uploader, ext='mp4'):
    """Generate filename matching existing convention.

    Uses smart truncation at word boundaries (max 70 chars for title).
    """
    # Sanitize and truncate title at word boundary
    sanitized_title = sanitize_title(title)
    sanitized_title, _ = truncate_title(sanitized_title)

    # Capitalize uploader
    capitalized_uploader = ' '.join(
        word.capitalize() for word in uploader.replace('_', ' ').split()
    )

    return f"{sanitized_title} - {capitalized_uploader}.{ext}"


def analyze_video_with_gemini(video_path, api_key=None):
    """Analyze video content using Gemini 1.5 Pro.

    Uses the File API for reliable video upload and processing.
    Returns detailed analysis of video content.
    """
    api_key = api_key or GEMINI_API_KEY
    if not api_key:
        return {'error': 'No Gemini API key provided', 'analysis': None}

    try:
        print(f"Starting Gemini video analysis for: {video_path}")

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Upload video to Gemini File API
        print("Uploading video to Gemini File API...")
        video_file = genai.upload_file(path=video_path)
        print(f"Upload complete. File name: {video_file.name}")

        # Wait for file to be processed
        print("Waiting for video processing...")
        max_wait = 120  # Maximum wait time in seconds
        wait_time = 0
        while video_file.state.name == "PROCESSING" and wait_time < max_wait:
            time.sleep(5)
            wait_time += 5
            video_file = genai.get_file(video_file.name)
            print(f"Processing... ({wait_time}s)")

        if video_file.state.name == "FAILED":
            return {'error': f'Gemini file processing failed: {video_file.state.name}', 'analysis': None}

        if video_file.state.name != "ACTIVE":
            return {'error': f'Gemini file not ready after {max_wait}s: {video_file.state.name}', 'analysis': None}

        print(f"Video ready. State: {video_file.state.name}")

        # Create the model and generate analysis
        model = genai.GenerativeModel('gemini-2.0-flash')

        prompt = """Analyze this video in detail. Provide a comprehensive analysis covering:

1. **👁️ Visual Content**
Describe what you see throughout the video - people, objects, settings, actions, transitions, visual effects, text overlays, and any on-screen graphics.

2. **🔊 Audio Content**
Describe the audio - speech (summarize what is said), music, sound effects, and overall audio quality.

3. **🎬 Style & Production**
Comment on the video style, editing techniques, pacing, and production quality.

4. **🎭 Mood & Tone**
Describe the overall mood, emotional tone, and atmosphere of the video.

5. **💡 Key Messages**
What are the main points, messages, or takeaways from this video?

6. **📁 Content Category**
What type of content is this? (e.g., tutorial, entertainment, educational, promotional, personal vlog, etc.)

Be specific and detailed in your analysis."""

        print("Generating video analysis...")
        response = model.generate_content([video_file, prompt])

        # Clean up - delete the uploaded file
        try:
            genai.delete_file(video_file.name)
            print("Cleaned up uploaded file")
        except Exception as cleanup_error:
            print(f"Warning: Failed to delete uploaded file: {cleanup_error}")

        analysis_text = response.text
        print(f"Analysis complete. Length: {len(analysis_text)} chars")

        return {
            'analysis': analysis_text,
            'model': 'gemini-2.0-flash',
            'error': None
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Gemini analysis error: {error_msg}")
        return {
            'error': error_msg,
            'analysis': None
        }


@functions_framework.http
def download_and_store(request):
    """Main Cloud Function entry point."""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    try:
        # Handle both JSON and form data
        request_json = request.get_json(force=True, silent=True)
        if not request_json:
            # Try parsing raw data
            raw_data = request.data
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode('utf-8')
            request_json = json.loads(raw_data)

        video_url = request_json.get('video_url')
        custom_filename = request_json.get('filename')
        extract_audio_flag = request_json.get('extract_audio', True)
        transcribe_audio_flag = request_json.get('transcribe_audio', True)
        analyze_video_flag = request_json.get('analyze_video', True)
        gemini_api_key = request_json.get('gemini_api_key')
        assemblyai_api_key = request_json.get('assemblyai_api_key')

        if not video_url:
            return ({'error': 'video_url is required'}, 400, headers)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Download video
            video_info = download_video(video_url, tmpdir)

            # Generate filename
            filename = custom_filename or generate_smart_filename(
                video_info['title'],
                video_info['uploader'],
                video_info['ext']
            )

            # Upload video to Cloud Storage
            storage_client = get_storage_client()
            video_file = upload_to_gcs(
                storage_client,
                video_info['filepath'],
                filename
            )

            response = {
                'success': True,
                'video': {
                    'file_name': filename,
                    'public_url': video_file['public_url'],
                    'size_bytes': video_file['size_bytes'],
                    'blob_name': video_file['blob_name'],
                },
                'metadata': {
                    'title': video_info['title'],
                    'duration': video_info['duration'],
                    'uploader': video_info['uploader'],
                    'video_id': video_info['video_id'],
                    'source': video_info['source'],
                    'thumbnail': video_info['thumbnail'],
                }
            }

            # Extract and upload audio if requested
            if extract_audio_flag:
                audio_path = extract_audio(video_info['filepath'], tmpdir)
                if audio_path:
                    audio_filename = filename.rsplit('.', 1)[0] + '.mp3'
                    audio_file = upload_to_gcs(
                        storage_client,
                        audio_path,
                        audio_filename
                    )
                    response['audio'] = {
                        'file_name': audio_filename,
                        'public_url': audio_file['public_url'],
                        'size_bytes': audio_file['size_bytes'],
                        'blob_name': audio_file['blob_name'],
                    }

                    # Transcribe audio if requested
                    if transcribe_audio_flag:
                        transcription_result = transcribe_audio(
                            audio_path,
                            api_key=assemblyai_api_key
                        )
                        response['transcription'] = transcription_result

            # Analyze video with Gemini if requested
            if analyze_video_flag:
                gemini_result = analyze_video_with_gemini(
                    video_info['filepath'],
                    api_key=gemini_api_key
                )
                response['gemini_analysis'] = gemini_result

            # Validate that all required fields are present and non-empty
            validation_result = validate_video_enrichment(response)
            response['validation'] = {
                'valid': validation_result['valid'],
                'errors': validation_result['errors'],
                'required_sections': REQUIRED_ANALYSIS_SECTIONS
            }

            # If validation failed, add to errors array for n8n handling
            if not validation_result['valid']:
                if 'errors' not in response:
                    response['errors'] = []
                response['errors'].extend(validation_result['errors'])
                print(f"Validation errors: {validation_result['errors']}")

            return (response, 200, headers)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error: {str(e)}\n{error_trace}")
        return ({'error': str(e), 'traceback': error_trace, 'success': False}, 500, headers)
