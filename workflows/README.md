# Bookmark Knowledge Base - n8n Workflows

This folder contains the n8n workflows for the bookmark enrichment system.

## Workflows

### Bookmark Processor
**File:** `Bookmark_Processor.json`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/process-bookmark`
**Status:** Active

Routes URLs to appropriate Cloud Function based on content type:
- Video URLs (TikTok, YouTube, etc.) → `video-enricher` Cloud Function
- Webpage URLs (articles, products, etc.) → `webpage-enricher` Cloud Function

**Triggers:**
- Notion Database Automation (recommended)
- Direct webhook call

**Manual Usage:**
```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/process-bookmark \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/article", "notion_page_id":"optional-page-id"}'
```

---

## Notion Automation Setup

To automatically process new bookmarks added to Notion:

1. Open your **Resources** database in Notion
2. Click the `⚡` button (or `...` → **Automations**)
3. Click **+ New automation**
4. Configure the trigger:
   - **When:** Page added to Resources
5. Click **+ Add action** → **Send webhook**
6. Configure the webhook:
   - **URL:** `https://royhen.app.n8n.cloud/webhook/process-bookmark`
   - **Body:** Include page properties (Link, id)
7. Save and enable the automation

The workflow will:
- Extract the URL from the `Link` property
- Detect content type (video, article, product, code)
- Enrich with AI analysis
- Update the Notion page with: Title, Type, AI Summary, Domain, Author, Status

---

### Video Processor
**File:** `Video_Processor.json`
**Webhook:** `https://royhen.app.n8n.cloud/webhook/analyze-video-complete`
**Status:** Active

Full video processing pipeline:
- Downloads video via Cloud Function
- Gemini 2.0 Flash video analysis
- AssemblyAI transcription
- ACRCloud music recognition
- GPT-4 Mini metadata generation
- Google Drive upload

**Processing time:** ~25-30 seconds per video

**Usage:**
```bash
curl -X POST https://royhen.app.n8n.cloud/webhook/analyze-video-complete \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@user/video/123"}'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         n8n Workflows                            │
│  (Orchestration - routing & data movement only)                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│     video-enricher        │   │    webpage-enricher       │
│     (Cloud Function)      │   │    (Cloud Function)       │
│                           │   │                           │
│ • yt-dlp download         │   │ • Fetch & parse HTML      │
│ • Gemini 2.0 Flash        │   │ • Extract metadata        │
│ • Store to GCS + Drive    │   │ • Gemini AI summary       │
└───────────────────────────┘   └───────────────────────────┘
```

## Credentials Required

| Credential | Used By | Purpose |
|------------|---------|---------|
| AssemblyAI API | Video Processor | Audio transcription |
| OpenAI API | Video Processor | GPT-4 Mini metadata |
| Google Drive OAuth2 | Video Processor | Video uploads |
| ACRCloud | Video Processor | Music recognition |
| Notion API | Bookmark Processor | Database updates |

## n8n Workflow IDs

| Workflow | ID |
|----------|-----|
| Video Processor | `7IGCrP5UdZ6wdbij` |
| Bookmark Processor | `DJVhLZKH7YIuvGv8` |

## Cost Estimates

| Workflow | Cost per Item |
|----------|---------------|
| Video processing | ~$0.017 |
| Webpage processing | ~$0.011 |

---

**Last Updated:** December 24, 2025
