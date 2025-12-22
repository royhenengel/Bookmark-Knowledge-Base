# TikTok Bookmark Knowledge Base

AI-powered TikTok video analysis system that automatically generates metadata, transcriptions, identifies music, and stores videos in Google Drive using n8n workflows.

[![Status](https://img.shields.io/badge/status-working-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## Overview

This project processes TikTok videos to generate comprehensive metadata including:
- **Smart Titles** (50-100 characters, SEO-optimized)
- **Content Tags** (topic, style, mood, format, purpose)
- **Rich Descriptions** (covering visual and audio content)
- **Audio Transcriptions** (via AssemblyAI)
- **Visual Analysis** (via GPT-4 Vision)
- **Music Recognition** (via ACRCloud - identifies songs with confidence scoring)
- **Google Drive Storage** (organized video library with descriptive filenames)

**Processing Time:** ~25-30 seconds per video
**Cost:** ~$0.017 per video (target: <$0.06)

## Features

### Working
- End-to-end video processing via n8n workflows
- GPT-4 Vision analysis of video cover images
- **AssemblyAI audio transcription** (96% accuracy, no file limits, faster)
- **ACRCloud music recognition** with:
  - Multiple song detection per video
  - 70% confidence threshold filtering
  - Support for both "music" and "humming" matches
  - Streaming service IDs (Spotify, Apple Music, Deezer)
- Automated Google Drive uploads with smart filenames
  - Format: `[Title up to 80 chars] - [Capitalized Author].mp4`
  - Example: `Unlock AI Simple Tutorials for Everyday Tasks - Sabrina Ramonov.mp4`
- GPT-4 Mini metadata generation
- Structured JSON output

### Planned
- RapidAPI Shazam fallback for low-confidence matches
- Batch processing interface
- Cost monitoring dashboard

## Architecture

Built with [n8n Cloud](https://n8n.io) - a low-code workflow automation platform.

### Workflow Structure

```
Webhook Trigger
    |
Get Video Info (sub-workflow)
    |
    +---> Visual Analysis (GPT-4)
    +---> Download Video ---> Upload to Google Drive
    |                    \--> Upload to AssemblyAI ---> Transcription
    +---> Download Audio ---> ACRCloud Music Recognition
    |
Merge All Results
    |
Generate Metadata (GPT-4 Mini)
    |
Format & Return JSON
```

## Output Format

```json
{
  "title": "Playful Pomeranian Enjoys a Relaxing Day on a Boat | Serene Sea Adventure",
  "description": "Watch this adorable Pomeranian as it joyfully lounges on a boat deck...",
  "tags": ["dogs", "Pomeranian", "boat", "relaxation", "outdoor adventure"],
  "transcription": "Full AssemblyAI transcription of spoken content...",
  "video_url": "https://www.tiktok.com/@username/video/123456",
  "video_id": "123456",
  "author": "username",
  "duration": 10,
  "music": {
    "tiktok": {
      "title": "original sound - artist",
      "artist": "artist"
    },
    "recognized_songs": [
      {
        "title": "Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "confidence": 85,
        "match_type": "music",
        "spotify_id": "abc123",
        "apple_music_id": "def456"
      }
    ],
    "recognition_status": "matched",
    "total_matches_found": 2,
    "matches_above_threshold": 1,
    "highest_confidence": 85
  },
  "visual_analysis": "Detailed GPT-4 Vision analysis...",
  "google_drive": {
    "file_id": "abc123",
    "file_name": "Video Title Up To 80 Characters - Username.mp4",
    "file_url": "https://drive.google.com/file/d/..."
  },
  "processed_at": "2025-12-22T06:38:00.000Z"
}
```

### Music Recognition Status

| Status | Description |
|--------|-------------|
| `matched` | At least one song identified with >=70% confidence |
| `low_confidence` | Songs detected but all below 70% threshold |
| `no_match` | No music fingerprints detected |

## Setup

### Prerequisites

- n8n Cloud account (https://n8n.io)
- OpenAI API key (GPT-4, GPT-4 Mini access)
- AssemblyAI API key (audio transcription)
- ACRCloud account (music recognition)
- Google Drive OAuth2 credentials
- RapidAPI key (for TikTok endpoint)

### Configuration

1. **Import n8n Workflows**
   - Import workflows from `workflows/` folder
   - Configure credentials in n8n:
     - OpenAI API
     - AssemblyAI API (Header Auth)
     - Google Drive OAuth2
     - RapidAPI Header Auth

2. **ACRCloud Setup**
   - Create account at [ACRCloud](https://www.acrcloud.com/)
   - Get Access Key and Access Secret
   - Credentials are configured in the workflow's Code node

3. **Activate Workflows**
   - Main: TikTok Video Complete Processor

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
| AssemblyAI (transcription) | ~$0.005 |
| ACRCloud (music recognition) | ~$0.001 |
| GPT-4 Mini (metadata) | ~$0.001 |
| RapidAPI (TikTok data) | Included |
| Google Drive storage | Included |

**Budget:** $50 for testing (~2,940 videos at actual rate)

## Music Recognition Details

### ACRCloud Integration

- **API Region:** Asia-Pacific (ap-southeast-1)
- **Authentication:** HMAC-SHA1 signature
- **Confidence Threshold:** 70% (configurable)
- **Match Types:** "music" (exact fingerprint) and "humming" (similar pattern)

### Output Fields

| Field | Description |
|-------|-------------|
| `recognized_songs` | Array of songs above confidence threshold |
| `total_matches_found` | All matches before filtering |
| `matches_above_threshold` | Matches that passed 70% filter |
| `highest_confidence` | Best match percentage |
| `all_matches_raw` | All matches including low-confidence (for debugging) |

### Per-Song Data

- Title, artist, album, release date
- Confidence score (percentage)
- Match type ("music" or "humming")
- Play offset in original song (milliseconds)
- Streaming IDs (Spotify, Apple Music, Deezer)

## Known Limitations

1. **Visual Analysis:** Based on cover image only (not full video frames)
2. **Transcription:** May be empty for music-only videos (expected)
3. **Music Recognition:** May not identify indie/original tracks not in ACRCloud's database
4. **Play Offset:** Shows position in matched song, not TikTok video timestamp

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

## Contributing

This is a personal project, but feedback and suggestions are welcome!

## License

MIT License - See [LICENSE](LICENSE) for details

## Acknowledgments

- Built with [n8n](https://n8n.io)
- Powered by [OpenAI](https://openai.com) (GPT-4 Vision, GPT-4 Mini)
- Transcription by [AssemblyAI](https://www.assemblyai.com)
- Music recognition by [ACRCloud](https://www.acrcloud.com)
- Video data via [RapidAPI TikTok endpoint](https://rapidapi.com)

---

**Last Updated:** December 22, 2025
**Status:** Working end-to-end with ACRCloud music recognition
