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

## Architecture

Built with n8n Cloud workflows.

### Main Workflow
**TikTok Video Complete Processor**
- Webhook: `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
- Processing time: ~25-30 seconds per video
- Status: Active and fully functional

### Flow
```
Webhook → Get Video Info
    → Visual Analysis (GPT-4 Vision)
    → Download Video → Google Drive + AssemblyAI Transcription
    → Download Audio → ACRCloud Music Recognition
    → Merge → Generate Metadata → Format Output → Respond
```

## Current Implementation

### What's Working
- End-to-end video processing
- GPT-4 Vision visual analysis (cover image)
- AssemblyAI audio transcription (96% accuracy)
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

## Output Format

```json
{
  "title": "Video Title",
  "description": "2-3 sentence description",
  "tags": ["tag1", "tag2"],
  "transcription": "Spoken content transcription",
  "video_url": "https://www.tiktok.com/...",
  "video_id": "123456",
  "author": "username",
  "duration": 10,
  "music": {
    "tiktok": {"title": "...", "artist": "..."},
    "recognized_songs": [...],
    "recognition_status": "matched|low_confidence|no_match",
    "highest_confidence": 85
  },
  "visual_analysis": "GPT-4 Vision analysis",
  "google_drive": {...},
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

**Budget:** $50 for testing (~2,940 videos)

## Configuration

### Required Credentials (in n8n)
- OpenAI API (GPT-4 Vision, GPT-4 Mini)
- AssemblyAI API (Header Auth)
- ACRCloud (configured in Code node)
- Google Drive OAuth2

### Workflows Location
See `workflows/` folder for workflow exports and documentation.

## Known Limitations

1. **Visual Analysis:** Only analyzes cover image, not full video frames
2. **Transcription:** May be empty for music-only videos
3. **Music Recognition:** May not identify indie/original tracks not in ACRCloud database
4. **Play Offset:** Shows position in matched song, not TikTok video timestamp

## Success Metrics

**Achieved:**
- Single video processing working end-to-end
- Accurate metadata generation
- Music recognition with confidence scoring
- Multi-song detection per video
- Processing time under 30 seconds

**Goals:**
- Process videos within budget
- Maintain consistent quality
- Zero errors in production
