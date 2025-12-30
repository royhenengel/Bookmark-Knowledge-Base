# Handoff Document: Bookmark Knowledge Base

Generated: 2025-12-29

---

<original_task>
Build an AI-powered bookmark enrichment system for Notion. The system automatically processes bookmarked videos and webpages to generate metadata, transcriptions, summaries, and more.

> **Note:** Raindrop.io sync is managed separately in [notion-workspace](../notion-workspace). See [notion-raindrop-sync-impl-specs.md](../notion-workspace/docs/notion-raindrop-sync-impl-specs.md).
</original_task>

<work_completed>
## Core Infrastructure (Complete)

### Cloud Functions (Deployed on GCP)
1. **video-enricher** (`video-downloader` on GCP - legacy name)
   - Endpoint: `https://us-central1-video-processor-rhe.cloudfunctions.net/video-downloader`
   - Location: `/video-enricher/main.py`
   - Capabilities:
     - TikTok download via yt-dlp (primary) with RapidAPI fallback
     - YouTube download with anti-bot measures (iOS/Android VR/TV client emulation)
     - Spotify podcast support (finds episodes on YouTube, downloads from there)
     - Gemini 2.0 Flash video analysis
     - AssemblyAI audio transcription
     - Google Cloud Storage for temp files
     - Smart filename generation

2. **webpage-enricher** (Deployed)
   - Endpoint: `https://us-central1-video-processor-rhe.cloudfunctions.net/webpage-enricher`
   - Location: `/webpage-enricher/main.py`
   - Capabilities:
     - Full Spotify Web API integration with token caching (commit 781ea57)
     - Podcast episode RSS feed lookup via iTunes API
     - AssemblyAI transcription for podcast audio
     - Gemini 2.0 Flash AI analysis and title cleaning
     - Content type detection (video, podcast, social, code, product, article)
     - Price extraction for product pages
     - Code snippet extraction for dev resources
     - Reading time calculation

### n8n Workflows (Active on royhen.app.n8n.cloud)
1. **Bookmark Processor** (ID: DJVhLZKH7YIuvGv8) - 21 nodes, ACTIVE
   - Webhook: `https://royhen.app.n8n.cloud/webhook/process-bookmark`
   - Routes videos → Video Processor webhook (for ACRCloud + Google Drive)
   - Routes webpages → webpage-enricher Cloud Function
   - Full Notion integration with page body content
   - Error handling with email notifications
   - Text chunking for Notion 2000-char limit (ADR-002)
   - Toggle formatting for AI Analysis, Transcript, Visual Analysis, Code Snippets, Music Recognition

2. **Video Processor** (ID: 7IGCrP5UdZ6wdbij) - 15 nodes, ACTIVE
   - Webhook: `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
   - **ACRCloud Music Recognition** - Full implementation with HMAC signature
     - Host: `identify-ap-southeast-1.acrcloud.com`
     - 70% minimum confidence threshold
     - Parses both `music` and `humming` matches
   - **Google Drive Upload** - Uploads to "TikTok Videos" folder
     - Folder ID: `1G0AhK4a9chK8bhYe6wIBgQD7HsVPHOhc`
     - Smart filename: `{title} - {author}.mp4`
   - AssemblyAI transcription (parallel path)
   - OpenAI GPT-4o-mini metadata generation

3. **GitHub to Notion Sync v3** (ID: K1d7SfqiO695kt5h) - 18 nodes, ACTIVE
4. **Notion to GitHub Sync** (ID: eew0KSgMDIhUKvUF) - 8 nodes, ACTIVE

### Documentation
- `/README.md` - Project overview, architecture diagram, setup instructions
- `/docs/ARCHITECTURE.md` - System design, component boundaries, data flows
- `/docs/SCHEMA_DESIGN.md` - Notion schema documentation
- `/docs/ADR.md` - Architecture Decision Records:
  - ADR-001: Complete Notion Integration (Dec 27, 2025)
  - ADR-002: Notion API Text Length Limit Handling (Dec 28, 2025)

### Recent Commits (Most Recent First)
- `781ea57` feat: Add Spotify Web API and podcast transcription support
- `69adf45` fix: Ensure ai_analysis returns string for Spotify episodes
- `21c2f4e` feat: Add Spotify podcast episode support via oEmbed API
- `6335264` feat: Add AssemblyAI transcription to video enricher
- `d2a8cfa` fix: Remove author from generated titles
- `04ef758` feat: Improve Notion page formatting with toggles and smart titles
- `9dd4593` feat: Complete Notion integration with page body content and error handling
- `5558574` refactor: Replace polling trigger with Notion automation webhook

### Notion Setup
- Database: **Resources** (ID: `2cf4df89-4a69-819f-941c-f3f8703ef620`)
- Properties: Title, Link, Type, Status, AI Summary, Domain, Author, Reading Time, Price
- Automation: Webhook trigger on page add to process-bookmark endpoint
</work_completed>

<work_remaining>
## Medium Priority
2. **Backlog Processor Workflow** - IMPLEMENTED (Dec 29, 2025)
   - Workflow ID: `aVKSwnST5LWpUHDI`
   - Queries Notion for Status = "Inbox" items
   - Processes in batches (configurable, default 10)
   - 5-second delay between items (rate limiting)
   - Run via Manual Trigger in n8n UI

3. **Error Recovery** - Partial
   - Email notifications work
   - No automatic retry mechanism for recoverable errors

4. **Podcast Index RSS Fallback** - TODO in code
   - `/video-enricher/main.py:225` has TODO for Podcast Index fallback
   - Currently fails if episode not found on YouTube

## Low Priority
5. **YouTube Cookie File Support** - Not implemented
   - Error message mentions YOUTUBE_COOKIE_FILE but not implemented
   - Would help with bot detection issues

6. **Rate Limiting** - Not implemented
   - ARCHITECTURE.md mentions batch processing with rate limits
   - Current system processes one at a time
</work_remaining>

<attempted_approaches>
## Spotify Podcast Support Evolution
1. **First attempt**: oEmbed API only
   - Limited metadata (title, thumbnail only)
   - Commit `21c2f4e`

2. **Improvement**: Spotify Web API integration
   - Full metadata (description, duration, show info, publisher)
   - Token caching for efficiency
   - Commit `781ea57`

3. **Transcription approach**: RSS feed via iTunes API
   - Search iTunes for show → get RSS URL
   - Parse RSS feed to find episode audio URL
   - Transcribe with AssemblyAI
   - Works for publicly-accessible podcast audio

## Bot Detection Issues
- YouTube download sometimes blocked by "Sign in to confirm" bot detection
- Attempted mitigation: Multiple player clients (iOS, Android VR, TV)
- Suggested but not implemented: Cookie file, residential proxy

## Notion Text Limits
- Initial implementation failed on long transcripts (>2000 chars)
- Fixed with `splitText()` helper function (ADR-002)
- Splits at word boundaries to preserve readability
</attempted_approaches>

<critical_context>
## API Keys Required (stored in Cloud Function env vars and n8n credentials)
- `GEMINI_API_KEY` - Google Gemini 2.0 Flash
- `ASSEMBLYAI_API_KEY` - Audio transcription
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` - Spotify Web API
- `RAPIDAPI_KEY` - TikTok fallback (hardcoded default exists)
- Notion integration token (in n8n)
- Google Cloud service account (in Cloud Functions)

## GCP Resources
- Project: `video-processor-rhe`
- Region: `us-central1`
- Storage Bucket: `video-processor-temp-rhe`
- Cloud Functions: `video-downloader`, `webpage-enricher`

## Design Principles (from ARCHITECTURE.md)
- Cloud Functions: Processing & Intelligence only
- n8n: Orchestration & Data Movement only
- Notion: Rich Data Storage & UI

## Notion 2000-char Limit
- All rich_text content must be split into chunks < 2000 chars
- `splitText()` function in Build Page Blocks node handles this
- Long content appears as multiple paragraph blocks within toggles

## Cost Per Bookmark
- Video: ~$0.017 (Gemini + AssemblyAI + ACRCloud + Cloud Function)
- Webpage: ~$0.011 (Gemini + Cloud Function)
</critical_context>

<current_state>
## Working Features
- New Notion bookmark → automatic enrichment via webhook
- Video processing (TikTok, YouTube) with transcription and Gemini analysis
- Webpage processing with type detection and AI analysis
- Spotify podcast episode support with transcription
- Page body content with toggle formatting
- Error notifications via email
- **ACRCloud music recognition** - Videos now route through Video Processor (fixed Dec 29, 2025)
- **Google Drive upload** - Videos saved to "TikTok Videos" folder (fixed Dec 29, 2025)

## Active Workflows
- `Bookmark Processor` (21 nodes) - Primary processor (tool-agnostic)
- `Video Processor` (15 nodes) - Video-specific processing
- `Backlog Processor` (15 nodes) - Batch process Inbox items
- `GitHub to Notion Sync v3` (18 nodes) - GitHub integration
- `Notion to GitHub Sync` (8 nodes) - Bidirectional GitHub sync

## Git Status
- Branch: `main`
- Clean working tree
- Last commit: `781ea57` (Spotify Web API support)

## Files Structure
```
/bookmark-knoledge-base/
├── video-enricher/main.py      # Video processing Cloud Function
├── webpage-enricher/main.py    # Webpage processing Cloud Function
├── workflows/                   # n8n workflow JSON exports
├── docs/                        # ARCHITECTURE.md, SCHEMA_DESIGN.md, ADR.md
├── notes/                       # Sample outputs
└── README.md                    # Project documentation
```

## Open Questions
1. ~~Is ACRCloud music recognition actually implemented?~~ **ANSWERED: Yes, in Video Processor workflow**
2. ~~Is Google Drive upload working?~~ **ANSWERED: Yes, in Video Processor workflow (folder: TikTok Videos)**
3. ~~Should Bookmark Processor call Video Processor for videos?~~ **FIXED: Dec 29, 2025 - Updated "Detect URL Type" node to route videos to Video Processor webhook**
</current_state>

---

## Recommended Next Steps

1. **Add Error Recovery** - Automatic retry for recoverable errors
2. **Add Schedule Trigger to Backlog Processor** - Optional daily/weekly auto-run
3. **Implement Podcast Index RSS Fallback** - For podcast transcription when YouTube fails

## Recently Fixed (Dec 29, 2025)

- **Built Backlog Processor workflow** - Batch process unprocessed bookmarks (Status = "Inbox")
  - Workflow ID: `aVKSwnST5LWpUHDI` (15 nodes, active)
  - Queries Notion for Inbox items, processes via Bookmark Processor webhook
  - Configurable batch size (default 10) and rate limiting (5s delay)
  - Run via Manual Trigger in n8n UI
- **Connected Bookmark Processor to Video Processor** - Videos from Notion now properly route through Video Processor workflow, enabling ACRCloud music recognition and Google Drive upload
- **Fixed data format compatibility** - Updated "Normalize Results" node to handle Video Processor output format:
  - Title: Now uses `generated_metadata.title` (GPT-4o-mini) instead of parsing Gemini analysis
  - Music: Extracts `recognized_songs` array from music object for proper toggle display
