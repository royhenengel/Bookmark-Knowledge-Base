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
- Downloads video metadata and files (video + audio separately)
- Performs visual analysis using GPT-4 Vision on cover image
- Transcribes audio using AssemblyAI
- Identifies music using ACRCloud (with confidence filtering)
- Generates metadata (title, description, tags) using GPT-4 Mini
- Uploads video to Google Drive with smart filename
- Returns comprehensive JSON response

**Processing time:** ~25-30 seconds per video

## Node Flow

```
Webhook
    |
Get Video Info (API call)
    |
    +---> Visual Analysis (GPT-4 Vision)
    |
    +---> Download Video ---> Upload to AssemblyAI ---> Transcription
    |                    \--> Merge with Metadata ---> Upload to Google Drive
    |
    +---> Download Audio ---> ACRCloud Prepare Signature ---> ACRCloud Music Recognition
    |
Merge Transcription & Visual
    |
Generate Metadata (GPT-4 Mini)
    |
Merge Metadata with Video
    |
Upload to Google Drive
    |
Merge ACRCloud with Output
    |
Format Final Output
    |
Respond to Webhook
```

## Output Format

```json
{
  "title": "50-100 character title",
  "description": "2-3 sentence description",
  "tags": ["tag1", "tag2", ...],
  "transcription": "AssemblyAI transcription",
  "video_url": "original TikTok URL",
  "video_id": "video ID",
  "author": "username",
  "duration": 10,
  "music": {
    "tiktok": {
      "title": "song title from TikTok",
      "artist": "artist name"
    },
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

- Videos uploaded to Google Drive with smart filenames
- **Filename Format:**
  - Title limited to 80 characters (preserves original casing and spaces)
  - Author capitalized from underscore format (e.g., `sabrina_ramonov` → `Sabrina Ramonov`)
  - Special characters removed from title
  - Example: `Unlock AI Simple Tutorials for Everyday Tasks - Sabrina Ramonov.mp4`
- Transcription will be empty for videos without speech
- All tags are content descriptors - NO audience tags like "viral" or "trending"
- Visual analysis is based on cover image only
- Music recognition may return low-confidence matches for indie/original tracks
- Multiple songs can be detected per video

## Last Updated

2025-12-22 - Added ACRCloud music recognition with multi-song support
