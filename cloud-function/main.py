import functions_framework
from google.oauth2 import service_account
from google.cloud import storage
import google.generativeai as genai
import yt_dlp
import tempfile
import subprocess
import os
import json
import traceback
import time
from datetime import timedelta

# Configuration
BUCKET_NAME = os.environ.get('GCS_BUCKET', 'video-processor-temp-rhe')
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')  # Required: set via Cloud Function environment variable


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


def download_video(url, tmpdir):
    """Download video - uses RapidAPI for TikTok, yt-dlp for others."""
    import requests

    # Detect source
    if 'tiktok' in url.lower():
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
        title = str(title)[:100] if title else 'Untitled'

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
    """Generate filename matching existing convention."""
    # Sanitize title (keep letters, numbers, spaces)
    sanitized_title = ''.join(c for c in title if c.isalnum() or c.isspace())
    sanitized_title = ' '.join(sanitized_title.split())[:80]  # Limit to 80 chars

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

1. **Visual Content**: Describe what you see throughout the video - people, objects, settings, actions, transitions, visual effects, text overlays, and any on-screen graphics.

2. **Audio Content**: Describe the audio - speech (summarize what is said), music, sound effects, and overall audio quality.

3. **Style & Production**: Comment on the video style, editing techniques, pacing, and production quality.

4. **Mood & Tone**: Describe the overall mood, emotional tone, and atmosphere of the video.

5. **Key Messages**: What are the main points, messages, or takeaways from this video?

6. **Content Category**: What type of content is this? (e.g., tutorial, entertainment, educational, promotional, personal vlog, etc.)

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
        analyze_video_flag = request_json.get('analyze_video', True)
        gemini_api_key = request_json.get('gemini_api_key')

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

            # Analyze video with Gemini if requested
            if analyze_video_flag:
                gemini_result = analyze_video_with_gemini(
                    video_info['filepath'],
                    api_key=gemini_api_key
                )
                response['gemini_analysis'] = gemini_result

            return (response, 200, headers)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error: {str(e)}\n{error_trace}")
        return ({'error': str(e), 'traceback': error_trace, 'success': False}, 500, headers)
