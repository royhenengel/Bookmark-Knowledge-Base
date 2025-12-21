# TikTok Bookmark Knowledge Base - Workflows

This folder contains the current working n8n workflows for the TikTok video analysis system.

## Active Workflows

### TikTok Complete Processor

**File:** `TikTok_Complete_Processor.json`
**Workflow ID:** `uBoLxqVCmR0Pk1Jk`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
**Status:** ✅ Active and Working

**What it does:**

- Receives TikTok video URLs via webhook
- Downloads video metadata and video file
- Performs visual analysis using GPT-4 Vision on cover image
- Transcribes audio using AssemblyAI
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
  "transcription": "assemblyai transcription",
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

## Node Flow

```text
Webhook → Get Video Info (API call) → [Visual Analysis + Download Video]
  ↓                                      ↓
Visual Analysis                   Download → Upload to Google Drive
  ↓                                      ↓
  ↓                              Upload to AssemblyAI
  ↓                                      ↓
  ↓                              Submit Transcription
  ↓                                      ↓
  ↓                              Wait 3s → Check Status → If Completed
  ↓                                      ↓ (loop until done)
  └──────────── Merge All ──────────────┘
                  ↓
          Generate Metadata (GPT-4 Mini)
                  ↓
          Format Final Output
                  ↓
        Respond to Webhook
```

## Credentials Required

- **AssemblyAI API** (ID: `assemblyai`)
  - Used for: Audio transcription with robust polling
- **OpenAI API** (ID: `p4lXz4PI3LIye0EB`)
  - Used for: GPT-4 Vision, GPT-4 Mini
- **Google Drive OAuth2** (ID: `ofFKlLc4IoxLD68F`)
  - Used for: Video uploads

## Cost Estimates

Target: ~$0.017 per video

- GPT-4 Vision (cover analysis): ~$0.01
- AssemblyAI (transcription): ~$0.005
- GPT-4 Mini (metadata generation): ~$0.001
- Google Drive storage: Included in plan

## Setup Instructions

See [ASSEMBLYAI_SETUP.md](ASSEMBLYAI_SETUP.md) for detailed setup instructions.

## Testing

Test the workflow:

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@sabrina_ramonov/video/7584566644308069662"}' \
  --max-time 180
```

## Notes

- Videos are currently uploaded to Google Drive root folder
- Transcription will be empty for videos without speech (music/ambient sound only)
- All tags are content descriptors - NO audience tags like "viral" or "trending"
- Visual analysis is based on cover image only (not full video frames)
- AssemblyAI polling: 3-second intervals until completion

## Last Updated

2025-12-21 - Working end-to-end with AssemblyAI transcription
