# Development Notes

Historical development notes and implementation details.

## Main Documentation

See the root-level docs for current system documentation:
- [README.md](../README.md) - System overview and setup
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design and boundaries
- [docs/SCHEMA_DESIGN.md](../docs/SCHEMA_DESIGN.md) - Notion schema design
- [workflows/README.md](../workflows/README.md) - n8n workflow documentation

## Notes in This Folder

| File | Description |
|------|-------------|
| [SAMPLE-OUTPUT.md](SAMPLE-OUTPUT.md) | Example output from video processing |

## Development History

### Phase 1: Video Processing (Dec 2025)
- TikTok video download via yt-dlp + RapidAPI fallback
- Gemini 2.0 Flash video analysis
- AssemblyAI transcription
- ACRCloud music recognition
- Google Drive storage

### Phase 2: Webpage Enrichment (Dec 2025)
- Notion schema design
- webpage-enricher Cloud Function for non-video URLs
- n8n Bookmark Processor workflow
- Clear system boundaries (processing vs orchestration)

### Phase 3: Backlog Processing (Planned)
- Process 6,500 existing bookmarks
- Batch processing with rate limiting
- Error recovery and monitoring

---

**Last Updated:** December 23, 2025
