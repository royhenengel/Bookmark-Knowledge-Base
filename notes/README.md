# TikTok Bookmark Knowledge Base

AI-powered TikTok video analysis system that generates metadata, transcriptions, and stores videos in Google Drive.

## Project Status: ✅ Working End-to-End

**Last Updated:** December 17, 2025

## What It Does

Processes TikTok videos to automatically generate:
- **Titles** (50-100 characters, descriptive, keyword-rich)
- **Tags** (topic, style, mood, format, purpose - NO audience tags)
- **Descriptions** (2-3 sentences covering visual AND audio content)
- **Transcriptions** (Full Whisper transcription of spoken content)
- **Visual Analysis** (GPT-4 Vision analysis of cover image)
- **Google Drive Storage** (Videos uploaded with structured naming)
- **Music Info** (Title and artist from TikTok metadata)

## Architecture

Built with n8n Cloud workflows:

### Main Workflow
**TikTok Video Complete Processor**
- Webhook: `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
- Processing time: ~25-30 seconds per video
- Status: Active and fully functional

### Flow
```
Webhook → Get Video Info → [Visual Analysis + Download Video]
  → Upload to Google Drive + Transcribe Audio
  → Merge → Generate Metadata → Format Output → Respond
```

## Current Implementation

### What's Working ✅
- End-to-end video processing
- GPT-4 Vision visual analysis (cover image)
- OpenAI Whisper audio transcription
- Google Drive video uploads
- GPT-4 Mini metadata generation (title, description, tags)
- Structured JSON output

### In Progress 🚧
- Shazam music identification (deferred)
- Google Drive folder organization (currently uploads to root)
- Batch processing interface

## Output Format

```json
{
  "title": "Playful Pomeranian Enjoys a Relaxing Day on a Boat | Serene Sea Adventure",
  "description": "Watch this adorable Pomeranian as it joyfully lounges...",
  "tags": ["dogs", "Pomeranian", "boat", "relaxation", "outdoor adventure"],
  "transcription": "Full whisper transcription...",
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

## Tag Guidelines

**Include:**
- Topic tags: cooking, fashion, tech, pets, travel
- Style tags: tutorial, comedy, storytelling, vlog
- Mood tags: joyful, relaxing, energetic, informative
- Format tags: short-form, time-lapse, POV
- Purpose tags: educational, entertaining, inspirational

**Exclude:**
- Audience tags: viral, trending, popular, fyp
- Generic tags: video, tiktok, content

## Testing

Test with a single video:
```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@scout2015/video/6718335390845095173"}'
```

## Cost Estimates

Target: ~$0.06 per video

Breakdown:
- GPT-4 Vision (cover analysis): ~$0.01
- Whisper (transcription): ~$0.01-0.02
- GPT-4 Mini (metadata): ~$0.001
- RapidAPI (TikTok data): Included
- Google Drive storage: Included

**Budget:** $50 approved for testing (~830 videos)

## Configuration

### Required Credentials (in n8n)
- OpenAI API (GPT-4 Vision, Whisper, GPT-4 Mini)
- Google Drive OAuth2
- RapidAPI (TikTok endpoint)

### Workflows Location
See `workflows/` folder for current workflow exports and documentation.

## Known Limitations

1. **Visual Analysis:** Only analyzes cover image, not full video frames
2. **Transcription:** May be empty for music-only or ambient sound videos
3. **Folder Structure:** Currently uploads to Google Drive root (planned: Media/TikTok/)
4. **Music ID:** Using TikTok metadata instead of Shazam (sufficient for now)

## Next Steps

1. Test with videos containing speech to validate transcription
2. Implement proper Google Drive folder structure
3. Add Shazam music identification
4. Create batch processing interface
5. Monitor costs across larger batches

## Success Metrics

✅ **Achieved:**
- Single video processing working end-to-end
- Accurate metadata generation
- Clean output format
- Processing time under 30 seconds

🎯 **Goals:**
- Process 830+ videos within $50 budget
- Maintain ~$0.06/video cost
- Consistent quality across batches
- Zero errors in production
