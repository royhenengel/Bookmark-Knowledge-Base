# TikTok Bookmark Knowledge Base

AI-powered TikTok video analysis system that automatically generates metadata, transcriptions, and stores videos in Google Drive using n8n workflows.

[![Status](https://img.shields.io/badge/status-working-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## Overview

This project processes TikTok videos to generate comprehensive metadata including:
- **Smart Titles** (50-100 characters, SEO-optimized)
- **Content Tags** (topic, style, mood, format, purpose)
- **Rich Descriptions** (covering visual and audio content)
- **Audio Transcriptions** (via OpenAI Whisper)
- **Visual Analysis** (via GPT-4 Vision)
- **Google Drive Storage** (organized video library)

**Processing Time:** ~25-30 seconds per video
**Cost:** ~$0.017 per video (target: <$0.06)

## Features

### ✅ Working
- End-to-end video processing via n8n workflows
- GPT-4 Vision analysis of video cover images
- OpenAI Whisper audio transcription
- Automated Google Drive uploads
- GPT-4 Mini metadata generation
- Structured JSON output

### 🚧 Planned
- Shazam music identification
- Google Drive folder organization (Media/TikTok/)
- Batch processing interface
- Cost monitoring dashboard

## Architecture

Built with [n8n Cloud](https://n8n.io) - a low-code workflow automation platform.

### Workflow Structure

```
Webhook Trigger
    ↓
Get Video Info (sub-workflow)
    ↓
[Visual Analysis (GPT-4) + Download Video]
    ↓
Upload to Google Drive + Transcribe Audio (Whisper)
    ↓
Merge Results (3 inputs)
    ↓
Generate Metadata (GPT-4 Mini)
    ↓
Format & Return JSON
```

## Output Format

```json
{
  "title": "Playful Pomeranian Enjoys a Relaxing Day on a Boat | Serene Sea Adventure",
  "description": "Watch this adorable Pomeranian as it joyfully lounges on a boat deck...",
  "tags": ["dogs", "Pomeranian", "boat", "relaxation", "outdoor adventure"],
  "transcription": "Full Whisper transcription of spoken content...",
  "video_url": "https://www.tiktok.com/@username/video/123456",
  "video_id": "123456",
  "author": "username",
  "duration": 10,
  "music": {
    "title": "original sound - artist",
    "artist": "artist"
  },
  "visual_analysis": "Detailed GPT-4 Vision analysis...",
  "google_drive": {
    "file_id": "abc123",
    "file_name": "username_123456.mp4",
    "file_url": "https://drive.google.com/file/d/..."
  },
  "processed_at": "2025-12-17T19:38:04.990Z"
}
```

## Setup

### Prerequisites

- n8n Cloud account (https://n8n.io)
- OpenAI API key (GPT-4, Whisper, GPT-4 Mini access)
- Google Drive OAuth2 credentials
- RapidAPI key (for TikTok endpoint)

### Configuration

1. **Import n8n Workflows**
   - Import workflows from `workflows/` folder
   - Configure credentials in n8n:
     - OpenAI API
     - Google Drive OAuth2
     - RapidAPI Header Auth

2. **Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Activate Workflows**
   - Main: TikTok Video Complete Processor
   - Sub: TikTok Video Info - No Code Node

## Usage

### Process a Single Video

```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@username/video/123456"}'
```

### Example Response

See [notes/SAMPLE-OUTPUT.md](notes/SAMPLE-OUTPUT.md) for a complete example with analysis.

## Documentation

- **[Workflows Documentation](workflows/README.md)** - Detailed workflow structure and configuration
- **[Project Notes](notes/README.md)** - Project status, architecture, and requirements
- **[Sample Output](notes/SAMPLE-OUTPUT.md)** - Real example with quality assessment

## Cost Breakdown

**Target:** <$0.06 per video
**Actual:** ~$0.017 per video

| Component | Cost per Video |
|-----------|---------------|
| GPT-4 Vision (cover analysis) | ~$0.01 |
| Whisper (transcription) | ~$0.006 |
| GPT-4 Mini (metadata) | ~$0.001 |
| RapidAPI (TikTok data) | Included |
| Google Drive storage | Included |

**Budget:** $50 for testing (~830 videos at target rate, ~2,940 at actual rate)

## Tag Guidelines

### Include
- **Topic:** cooking, fashion, tech, pets, travel
- **Style:** tutorial, comedy, storytelling, vlog
- **Mood:** joyful, relaxing, energetic, informative
- **Format:** short-form, time-lapse, POV
- **Purpose:** educational, entertaining, inspirational

### Exclude
- **Audience tags:** viral, trending, popular, fyp
- **Generic tags:** video, tiktok, content

## Known Limitations

1. **Visual Analysis:** Based on cover image only (not full video frames)
2. **Transcription:** May be empty for music-only videos (expected)
3. **Folder Structure:** Currently uploads to Google Drive root
4. **Music ID:** Uses TikTok metadata instead of Shazam

## Contributing

This is a personal project, but feedback and suggestions are welcome!

## License

MIT License - See [LICENSE](LICENSE) for details

## Acknowledgments

- Built with [n8n](https://n8n.io)
- Powered by [OpenAI](https://openai.com) (GPT-4, Whisper)
- Video data via [RapidAPI TikTok endpoint](https://rapidapi.com)

---

**Last Updated:** December 17, 2025
**Status:** ✅ Working end-to-end
