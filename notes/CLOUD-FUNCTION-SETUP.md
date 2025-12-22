# Cloud Function Setup Guide

Video Download & Storage Service for handling large files outside n8n.

## Overview

This Cloud Function:
- Downloads videos from TikTok (via RapidAPI) and YouTube (via yt-dlp)
- Uploads to Google Cloud Storage
- Extracts audio (MP3) using FFmpeg
- Returns public URLs for API consumption

**n8n never handles large binaries** - only URLs.

## Architecture

```
n8n (webhook)
    │
    ▼
Cloud Function (download + upload)
    │
    ▼
Google Cloud Storage (public URLs)
    │
    ├──► AssemblyAI (video URL)
    ├──► GPT-4 Vision (thumbnail URL)
    └──► ACRCloud (audio URL via n8n download)
```

## Deployed Resources

| Resource | Value |
|----------|-------|
| Project | `video-processor-rhe` |
| Function Name | `video-downloader` |
| Function URL | `https://us-central1-video-processor-rhe.cloudfunctions.net/video-downloader` |
| Storage Bucket | `video-processor-temp-rhe` |
| Region | `us-central1` |
| Runtime | Python 3.11 |
| Memory | 512MB |
| Timeout | 540s (9 minutes) |
| Generation | Gen 2 |

## API Usage

### Request

```bash
curl -X POST https://us-central1-video-processor-rhe.cloudfunctions.net/video-downloader \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.tiktok.com/@username/video/123456",
    "extract_audio": true
  }'
```

### Response

```json
{
  "success": true,
  "video": {
    "file_name": "Video Title - Username.mp4",
    "public_url": "https://storage.googleapis.com/video-processor-temp-rhe/videos/...",
    "size_bytes": 2953029,
    "blob_name": "videos/Video Title - Username.mp4"
  },
  "audio": {
    "file_name": "Video Title - Username.mp3",
    "public_url": "https://storage.googleapis.com/video-processor-temp-rhe/videos/...",
    "size_bytes": 182451,
    "blob_name": "videos/Video Title - Username.mp3"
  },
  "metadata": {
    "title": "Original Video Title",
    "duration": 10,
    "uploader": "username",
    "video_id": "123456",
    "source": "tiktok",
    "thumbnail": "https://..."
  }
}
```

## Source Code

### main.py

Located at: `cloud-function/main.py`

Key functions:
- `download_and_store()` - Main entry point
- `download_video()` - Routes to TikTok or YouTube downloader
- `download_tiktok_video()` - Uses RapidAPI to bypass IP blocks
- `download_with_ytdlp()` - Uses yt-dlp for YouTube/other sources
- `extract_audio()` - Uses FFmpeg to extract MP3
- `upload_to_gcs()` - Uploads to Cloud Storage with public URL
- `generate_smart_filename()` - Creates `Title - Author.ext` format

### requirements.txt

```
functions-framework==3.*
google-auth==2.*
google-cloud-storage>=2.14.0
yt-dlp>=2024.1.1
requests>=2.31.0
```

## Deployment

### Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed
3. Authenticated: `gcloud auth login`

### Deploy Command

```bash
cd cloud-function

# Read service account JSON
SERVICE_ACCOUNT_JSON=$(python3 -c "import json; print(json.dumps(json.load(open('/path/to/service-account.json'))))")

# Deploy
gcloud functions deploy video-downloader \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=download_and_store \
  --trigger-http \
  --allow-unauthenticated \
  --timeout=540s \
  --memory=512MB \
  --set-env-vars="GOOGLE_SERVICE_ACCOUNT=${SERVICE_ACCOUNT_JSON}" \
  --project=video-processor-rhe
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_SERVICE_ACCOUNT` | JSON string of service account credentials |
| `GCS_BUCKET` | Cloud Storage bucket name (default: `video-processor-temp-rhe`) |
| `RAPIDAPI_KEY` | RapidAPI key for TikTok downloads |

## Cloud Storage Setup

The bucket is configured with public access via IAM:

```bash
# Create bucket
gcloud storage buckets create gs://video-processor-temp-rhe \
  --location=us-central1 \
  --uniform-bucket-level-access

# Make public
gcloud storage buckets add-iam-policy-binding gs://video-processor-temp-rhe \
  --member="allUsers" \
  --role="roles/storage.objectViewer"
```

## Video Sources

### TikTok
- Uses RapidAPI endpoint: `tiktok-video-no-watermark2.p.rapidapi.com`
- Bypasses Google Cloud IP blocks
- Returns HD video when available

### YouTube
- Uses yt-dlp library
- Supports various formats
- No IP restrictions from Cloud Functions

## Filename Format

Files are named using this format:
```
[Sanitized Title up to 80 chars] - [Capitalized Author].ext
```

Example:
```
Unlock AI Simple Tutorials for Everyday Tasks - Sabrina Ramonov.mp4
Unlock AI Simple Tutorials for Everyday Tasks - Sabrina Ramonov.mp3
```

## Cost Estimates

| Resource | Free Tier | Estimated Cost |
|----------|-----------|----------------|
| Cloud Functions | 2M invocations/month | ~$0.0000004/invocation |
| Cloud Functions compute | 400K GB-seconds | ~$0.000024/GB-second |
| Cloud Storage | 5GB/month | $0.026/GB/month |
| Egress | 1GB/month | $0.12/GB after |

**Per video (30s TikTok):**
- Function runtime: ~15-30 seconds
- Memory: 512MB
- Storage: ~3MB video + ~0.2MB audio
- **Cost: ~$0.0004 per video**

## Troubleshooting

### "RapidAPI error: Unknown error"
- RapidAPI may be rate limiting the Cloud Function IP
- Wait a few minutes and retry
- Check RapidAPI dashboard for usage limits

### Function timeout
- Increase timeout: `--timeout=540s` (max for Gen 2)
- For very long videos, consider increasing memory

### "Permission denied" on Cloud Storage
- Ensure bucket has public IAM policy
- Check service account has `storage.objectCreator` role

### yt-dlp extraction fails
- Some videos may be geo-restricted or private
- Update yt-dlp version in requirements.txt

### Audio extraction fails
- FFmpeg is included in Python runtime by default
- Check video has audio track

## Monitoring

### View Logs
```bash
gcloud functions logs read video-downloader --region=us-central1 --limit=50
```

### Check Function Status
```bash
gcloud functions describe video-downloader --region=us-central1
```

## Security Notes

1. **Function Authentication:** Currently open (`--allow-unauthenticated`) for n8n access
2. **Service Account:** Has minimal permissions (Cloud Storage only)
3. **API Keys:** Stored as environment variables, not in code
4. **Bucket Access:** Public read, private write

## Files

| File | Description |
|------|-------------|
| `cloud-function/main.py` | Cloud Function source code |
| `cloud-function/requirements.txt` | Python dependencies |
| `/tmp/deploy_function.sh` | Deployment script |
| `/tmp/video-processor-service-account.json` | Service account key (local only) |

---

**Last Updated:** December 22, 2025
**Status:** Deployed and working
