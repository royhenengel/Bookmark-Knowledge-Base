# TikTok Bookmark Knowledge Base - Workflows

This folder contains the n8n workflows for the TikTok video analysis system.

## Active Workflows

### TikTok Complete Processor

**File:** `TikTok_Complete_Processor.json`
**Workflow ID:** `7IGCrP5UdZ6wdbij`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
**Status:** Active and Working

**What it does:**

- Receives TikTok video URLs via webhook
- Calls Cloud Function to download video and upload to Cloud Storage
- Performs visual analysis using GPT-4 Vision on thumbnail
- Transcribes audio using AssemblyAI (URL-based, no upload needed)
- Identifies music using ACRCloud (with confidence filtering)
- Generates metadata (title, description, tags) using GPT-4 Mini
- Uploads video to Google Drive with smart filename
- Returns comprehensive JSON response

**Processing time:** ~25-30 seconds per video

## Architecture

The workflow uses a Cloud Function to handle large file downloads, eliminating n8n memory limitations.

```
┌─────────────────────────────────────────────────────────────────┐
│                         n8n Workflow                             │
│  (Orchestration - works with URLs only)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Cloud Function                                 │
│  (Downloads video via RapidAPI, uploads to Cloud Storage)       │
│  URL: us-central1-video-processor-rhe.cloudfunctions.net        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Cloud Storage                                  │
│  Bucket: video-processor-temp-rhe                               │
│  Returns public URLs for video and audio                        │
└─────────────────────────────────────────────────────────────────┘
```

## Node Flow

```
Webhook
    │
    ▼
Cloud Function Download ─────────────────────────────────────────┐
    │ (POST to Cloud Function, returns video/audio URLs)         │
    │                                                              │
    ├──► Submit Transcription (AssemblyAI URL-based)              │
    │         │                                                    │
    │         ▼                                                    │
    │    Wait 3 Seconds ──► Check Status ──► If Completed ───────┤
    │                              │               │               │
    │                              └───────────────┘ (loop)        │
    │                                                              │
    ├──► Visual Analysis (GPT-4 Vision on thumbnail) ────────────┤
    │                                                              │
    └──► Download Audio from Storage ──► ACRCloud Signature       │
              │                                                    │
              ▼                                                    │
         ACRCloud Music Recognition ─────────────────────────────►│
                                                                   │
                                    Merge Transcription & Visual ◄┘
                                              │
                                              ▼
                                    Generate Metadata (GPT-4 Mini)
                                              │
                                              ▼
                                    Download Video from Storage
                                              │
                                              ▼
                                    Merge Metadata with Video
                                              │
                                              ▼
                                    Upload to Google Drive
                                              │
                                              ▼
                                    Merge ACRCloud with Output
                                              │
                                              ▼
                                    Format Final Output
                                              │
                                              ▼
                                    Respond to Webhook
```

## Key Nodes

### Cloud Function Download
- **Type:** HTTP Request (POST)
- **URL:** `https://us-central1-video-processor-rhe.cloudfunctions.net/video-downloader`
- **Timeout:** 300 seconds (5 minutes)
- **Returns:**
  - `video.public_url` - Cloud Storage URL for video
  - `audio.public_url` - Cloud Storage URL for audio (MP3)
  - `metadata` - title, duration, uploader, video_id, source, thumbnail

### Submit Transcription
- **Type:** HTTP Request (POST)
- **URL:** `https://api.assemblyai.com/v2/transcript`
- **Note:** Uses URL directly - no binary upload needed!

### Download Audio from Storage
- **Type:** HTTP Request (GET)
- **Purpose:** Downloads small MP3 file (~180KB) for ACRCloud
- **Source:** Cloud Storage audio URL

### Download Video from Storage
- **Type:** HTTP Request (GET)
- **Purpose:** Downloads video for Google Drive upload
- **Source:** Cloud Storage video URL

## Output Format

```json
{
  "title": "50-100 character title",
  "description": "2-3 sentence description",
  "tags": ["tag1", "tag2", ...],
  "transcription": "AssemblyAI transcription",
  "video_url": "Cloud Storage URL",
  "video_id": "video ID",
  "author": "username",
  "duration": 10,
  "source": "tiktok",
  "music": {
    "recognized_songs": [
      {
        "title": "Recognized Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "confidence": 85,
        "match_type": "music",
        "play_offset_ms": 55000,
        "spotify_id": "...",
        "apple_music_id": "...",
        "deezer_id": "..."
      }
    ],
    "recognition_status": "matched|low_confidence|no_match",
    "total_matches_found": 2,
    "matches_above_threshold": 1,
    "highest_confidence": 85,
    "all_matches_raw": [...]
  },
  "visual_analysis": "GPT-4 Vision analysis",
  "google_drive": {
    "file_id": "Google Drive file ID",
    "file_name": "Video Title - Author.mp4",
    "file_url": "Google Drive URL"
  },
  "cloud_storage": {
    "video_url": "Cloud Storage video URL",
    "audio_url": "Cloud Storage audio URL",
    "video_size_bytes": 2953029,
    "audio_size_bytes": 182451
  },
  "processed_at": "ISO timestamp"
}
```

## Credentials Required

| Credential | ID | Used For |
|------------|-----|----------|
| AssemblyAI API | `eJYyx8goZbb1aVw9` | Audio transcription (Header Auth) |
| OpenAI API | `p4lXz4PI3LIye0EB` | GPT-4 Vision, GPT-4 Mini |
| Google Drive OAuth2 | `ofFKlLc4IoxLD68F` | Video uploads |
| ACRCloud | Configured in Code node | Music recognition (HMAC-SHA1) |

**Note:** Cloud Function does not require n8n credentials - it's publicly accessible.

## ACRCloud Configuration

ACRCloud credentials are configured directly in the "ACRCloud Prepare Signature" Code node:

- **Host:** `identify-ap-southeast-1.acrcloud.com`
- **Access Key:** Configured in workflow
- **Access Secret:** Configured in workflow
- **Signature:** HMAC-SHA1 generated per request

### Confidence Threshold

The minimum confidence threshold is set to **70%** in the "Format Final Output" Code node. Songs below this threshold are included in `all_matches_raw` but excluded from `recognized_songs`.

## Cost Estimates

Target: ~$0.017 per video

| Component | Cost |
|-----------|------|
| GPT-4 Vision (cover analysis) | ~$0.01 |
| AssemblyAI (transcription) | ~$0.005 |
| ACRCloud (music recognition) | ~$0.001 |
| GPT-4 Mini (metadata generation) | ~$0.001 |
| Cloud Function | ~$0.0004 |
| Google Cloud Storage | Minimal |
| Google Drive storage | Included |

## Testing

Test the workflow:

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@username/video/123456"}' \
  --max-time 180
```

## Notes

- **No Binary Handling in n8n:** The workflow only downloads small files (MP3 for ACRCloud, video for GDrive upload from Cloud Storage)
- **Cloud Function handles large files:** Video download from TikTok happens in Cloud Function, not n8n
- **AssemblyAI URL-based:** No need to upload binary - just pass the Cloud Storage URL
- Videos uploaded to Google Drive with smart filenames
- **Filename Format:**
  - Title limited to 80 characters (preserves original casing and spaces)
  - Author capitalized from underscore format (e.g., `sabrina_ramonov` → `Sabrina Ramonov`)
  - Special characters removed from title
  - Example: `Unlock AI Simple Tutorials for Everyday Tasks - Sabrina Ramonov.mp4`
- Transcription will be empty for videos without speech
- All tags are content descriptors - NO audience tags like "viral" or "trending"
- Visual analysis is based on thumbnail only
- Music recognition may return low-confidence matches for indie/original tracks
- Multiple songs can be detected per video

## Removed Nodes

The following nodes from the old workflow were removed:

| Node | Reason |
|------|--------|
| Get Video Info | Replaced by Cloud Function |
| Download Video | Replaced by Cloud Function |
| Upload to AssemblyAI | AssemblyAI now uses URL directly |

## Last Updated

2025-12-22 - Updated to Cloud Function architecture
