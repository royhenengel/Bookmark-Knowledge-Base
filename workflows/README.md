# TikTok Bookmark Knowledge Base - Workflows

This folder contains the current working n8n workflows for the TikTok video analysis system.

## Active Workflows

### 1. TikTok Complete Processor (Main Workflow)
**File:** `TikTok_Complete_Processor_CURRENT.json`
**Workflow ID:** `jwb1PoXYuYP2a37M`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
**Status:** ✅ Active and Working

**What it does:**
- Receives TikTok video URLs via webhook
- Downloads video metadata and video file
- Performs visual analysis using GPT-4 Vision on cover image
- Transcribes audio using OpenAI Whisper
- Uploads video to Google Drive
- Generates metadata (title, description, tags) using GPT-4 Mini
- Returns comprehensive JSON response

**Processing time:** ~25-30 seconds per video

**Output format:**
```json
{
  "title": "50-100 character title",
  "description": "2-3 sentence description",
  "tags": ["tag1", "tag2", ...],
  "transcription": "whisper transcription",
  "video_url": "original tiktok url",
  "video_id": "video id",
  "author": "username",
  "duration": 10,
  "music": {
    "title": "song title",
    "artist": "artist name"
  },
  "visual_analysis": "detailed gpt-4 vision analysis",
  "google_drive": {
    "file_id": "google drive file id",
    "file_name": "author_videoid.mp4",
    "file_url": "google drive url"
  },
  "processed_at": "ISO timestamp"
}
```

### 2. TikTok Video Info - Sub Workflow
**File:** `TikTok_Video_Info_SubWorkflow_CURRENT.json`
**Workflow ID:** `YIreQfG1Uk8xa7KU`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/process-video-nocode`
**Status:** ✅ Active (called by main workflow)

**What it does:**
- Fetches TikTok video metadata via RapidAPI
- Extracts video URLs, cover images, author info, music details
- Returns structured data to calling workflow

## Node Flow

```
Main Workflow:
Webhook → Get Video Info (sub-workflow) → [Visual Analysis + Download Video]
  → Upload to Google Drive + Transcribe Audio → Merge All (3 inputs)
  → Generate Metadata → Format Output → Respond to Webhook
```

## Credentials Required

- **OpenAI API** (ID: `p4lXz4PI3LIye0EB`)
  - Used for: GPT-4 Vision, Whisper, GPT-4 Mini
- **Google Drive OAuth2** (ID: `ofFKlLc4IoxLD68F`)
  - Used for: Video uploads
- **RapidAPI Header Auth** (ID: `2JWLyhxNmaGziSYB`)
  - Used for: TikTok metadata fetching

## Cost Estimates

Target: ~$0.06 per video
- GPT-4 Vision (cover analysis): ~$0.01
- Whisper (transcription): ~$0.01
- GPT-4 Mini (metadata generation): ~$0.001
- Google Drive storage: Included in plan
- RapidAPI calls: Included in plan

## Testing

Test the workflow:
```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@scout2015/video/6718335390845095173"}'
```

## Notes

- Videos are currently uploaded to Google Drive root folder
- Transcription may be empty for videos without speech (music/ambient sound only)
- All tags are content descriptors - NO audience tags like "viral" or "trending"
- Visual analysis is based on cover image only (not full video frames)

## Last Updated

2025-12-17 - Working end-to-end with Whisper transcription
