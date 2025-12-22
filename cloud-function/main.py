import functions_framework
from google.oauth2 import service_account
from google.cloud import storage
import yt_dlp
import tempfile
import subprocess
import os
import json
import traceback
from datetime import timedelta

# Configuration
BUCKET_NAME = os.environ.get('GCS_BUCKET', 'video-processor-temp-rhe')
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


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
    """Download TikTok video using RapidAPI to bypass IP blocks."""
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

    return {
        'filepath': filepath,
        'title': video_data.get('title', 'Untitled'),
        'duration': video_data.get('duration', 0),
        'ext': 'mp4',
        'uploader': video_data.get('author', {}).get('unique_id', 'Unknown'),
        'video_id': video_id,
        'source': 'tiktok',
        'thumbnail': video_data.get('cover'),
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

            return (response, 200, headers)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error: {str(e)}\n{error_trace}")
        return ({'error': str(e), 'traceback': error_trace, 'success': False}, 500, headers)
