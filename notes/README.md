# TikTok Bookmark Knowledge Base

AI-powered TikTok video analysis system that generates metadata, transcriptions, identifies music, and stores videos in Google Drive.

## Project Status: Working End-to-End

**Last Updated:** December 22, 2025

## What It Does

Processes TikTok videos to automatically generate:
- **Titles** (50-100 characters, descriptive, keyword-rich)
- **Tags** (topic, style, mood, format, purpose - NO audience tags)
- **Descriptions** (2-3 sentences covering visual AND audio content)
- **Transcriptions** (AssemblyAI transcription of spoken content)
- **Visual Analysis** (GPT-4 Vision analysis of cover image)
- **Music Recognition** (ACRCloud with confidence scoring and multi-song support)
- **Google Drive Storage** (Videos uploaded with structured naming)
- **Cloud Storage Backup** (Videos and audio stored in Google Cloud Storage)

## Architecture

Built with n8n Cloud workflows + Google Cloud Functions.

### Two-Tier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         n8n Cloud                                │
│  (Orchestration - handles URLs only, no large binaries)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Google Cloud Function                          │
│  (Downloads videos, uploads to Cloud Storage, returns URLs)     │
│  URL: us-central1-video-processor-rhe.cloudfunctions.net        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Google Cloud Storage                           │
│  Bucket: video-processor-temp-rhe                               │
│  (Public URLs for video and audio)                              │
└─────────────────────────────────────────────────────────────────┘
```

### Why Cloud Function?

- **Problem:** n8n Cloud has ~256MB memory limit per execution
- **Problem:** TikTok videos can exceed this limit
- **Solution:** Cloud Function handles all binary operations
- **Result:** n8n only works with URLs, no file size limits

### Main Workflow
**TikTok Video Complete Processor**
- Webhook: `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
- Processing time: ~25-30 seconds per video
- Status: Active and fully functional

### Flow
```
Webhook → Cloud Function Download
    → Submit Transcription (URL) → Poll → Merge
    → Visual Analysis (thumbnail) → Merge
    → Download Audio → ACRCloud → Merge
    → Generate Metadata → Download Video → Upload to GDrive
    → Format Output → Respond
```

## Current Implementation

### What's Working
- End-to-end video processing via n8n + Cloud Function
- Cloud Function handles video download (no file size limits)
- GPT-4 Vision visual analysis (cover image)
- AssemblyAI audio transcription (96% accuracy, URL-based)
- ACRCloud music recognition with:
  - Multiple song detection
  - 70% confidence threshold
  - Streaming service IDs
- Google Drive video uploads with smart filenames
- GPT-4 Mini metadata generation
- Structured JSON output

### Planned
- RapidAPI Shazam fallback for low-confidence matches
- Batch processing interface
- Cost monitoring dashboard
- Gemini 1.5 Pro for full video analysis (not just cover image)

## Output Format

```json
{
  "title": "Video Title",
  "description": "2-3 sentence description",
  "tags": ["tag1", "tag2"],
  "transcription": "Spoken content transcription",
  "video_url": "https://storage.googleapis.com/...",
  "video_id": "123456",
  "author": "username",
  "duration": 10,
  "source": "tiktok",
  "music": {
    "recognized_songs": [...],
    "recognition_status": "matched|low_confidence|no_match",
    "highest_confidence": 85
  },
  "visual_analysis": "GPT-4 Vision analysis",
  "google_drive": {...},
  "cloud_storage": {
    "video_url": "...",
    "audio_url": "...",
    "video_size_bytes": 2953029,
    "audio_size_bytes": 182451
  },
  "processed_at": "ISO timestamp"
}
```

## Tag Guidelines

**Include:**
- Topic: cooking, fashion, tech, pets, travel
- Style: tutorial, comedy, storytelling, vlog
- Mood: joyful, relaxing, energetic, informative
- Format: short-form, time-lapse, POV
- Purpose: educational, entertaining, inspirational

**Exclude:**
- Audience tags: viral, trending, popular, fyp
- Generic tags: video, tiktok, content

## Testing

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@username/video/123456"}'
```

## Cost Estimates

Target: ~$0.017 per video

| Component | Cost |
|-----------|------|
| GPT-4 Vision | ~$0.01 |
| AssemblyAI | ~$0.005 |
| ACRCloud | ~$0.001 |
| GPT-4 Mini | ~$0.001 |
| Cloud Function | ~$0.0004 |

**Budget:** $50 for testing (~2,940 videos)

## Infrastructure

### Google Cloud Resources

| Resource | Details |
|----------|---------|
| Project | `video-processor-rhe` |
| Cloud Function | `video-downloader` |
| Storage Bucket | `video-processor-temp-rhe` |
| Region | `us-central1` |

### n8n Cloud

| Resource | Details |
|----------|---------|
| Workflow | TikTok Video Complete Processor |
| Webhook | `/webhook/analyze-video-complete` |

## Configuration

### Required Credentials (in n8n)
- OpenAI API (GPT-4 Vision, GPT-4 Mini)
- AssemblyAI API (Header Auth)
- ACRCloud (configured in Code node)
- Google Drive OAuth2

### Cloud Function
- Publicly accessible (no credentials needed in n8n)
- Uses RapidAPI for TikTok downloads
- Uses yt-dlp for YouTube downloads

### Documentation
- [Cloud Function Setup](CLOUD-FUNCTION-SETUP.md)
- [Workflow Details](../workflows/README.md)

## Known Limitations

1. **Visual Analysis:** Only analyzes cover image, not full video frames
2. **Transcription:** May be empty for music-only videos
3. **Music Recognition:** May not identify indie/original tracks not in ACRCloud database
4. **Play Offset:** Shows position in matched song, not TikTok video timestamp
5. **RapidAPI Rate Limits:** May temporarily rate limit Cloud Function IPs

## Success Metrics

**Achieved:**
- Single video processing working end-to-end
- No file size limitations (Cloud Function handles large files)
- Accurate metadata generation
- Music recognition with confidence scoring
- Multi-song detection per video
- Processing time under 30 seconds

**Goals:**
- Process videos within budget
- Maintain consistent quality
- Zero errors in production
