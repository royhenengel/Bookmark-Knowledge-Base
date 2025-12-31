# Bookmark Knowledge Base

AI-powered bookmark enrichment system for Notion. Automatically processes videos and webpages to generate metadata, transcriptions, summaries, and more.

> **Raindrop.io sync** is managed separately in [notion-workspace](../notion-workspace). See [notion-raindrop-sync-impl-specs.md](../notion-workspace/docs/notion-raindrop-sync-impl-specs.md).

[![Status](https://img.shields.io/badge/status-active-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## Overview

Save a bookmark to Notion and the system automatically:

**For Videos (TikTok, YouTube):**
- Downloads and stores in Google Drive
- Full video analysis via Gemini 2.0 Flash
- Audio transcription via AssemblyAI
- Music recognition via ACRCloud
- Generates SEO-optimized titles, tags, descriptions

**For Webpages (Articles, Products, Code):**
- Extracts metadata (title, author, publish date)
- Detects content type (article, product, code, social)
- Generates AI summary and analysis
- Extracts prices from product pages
- Extracts code snippets from dev resources

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Notion                                     │
│                    (Resources Database)                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Webhook on new bookmark
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION (n8n)                             │
│   • Routes URLs to appropriate processor                             │
│   • Updates Notion with enriched data                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│     video-enricher        │   │    webpage-enricher       │
│     (Cloud Function)      │   │    (Cloud Function)       │
│                           │   │                           │
│ • yt-dlp download         │   │ • Fetch & parse HTML      │
│ • Gemini 2.0 Flash        │   │ • Extract metadata        │
│ • AssemblyAI transcription│   │ • Gemini AI summary       │
│ • ACRCloud music ID       │   │ • Price extraction        │
│ • GCS + Drive storage     │   │ • Code snippet extraction │
└───────────────────────────┘   └───────────────────────────┘
```

### Design Principles

| System | Responsibility | NOT Responsible For |
|--------|----------------|---------------------|
| **Cloud Functions** | Processing & Intelligence | Data storage, orchestration |
| **n8n** | Orchestration & Data Movement | Business logic, heavy processing |
| **Notion** | Rich Data Storage & UI | Processing, external integrations |

## Cloud Functions

### video-enricher
Processes video URLs (TikTok, YouTube, etc.)

**Endpoint:** `https://us-central1-video-processor-rhe.cloudfunctions.net/video-downloader`
> Note: GCP function name is still `video-downloader` (legacy). Local folder is `video-enricher`.

```bash
curl -X POST $ENDPOINT \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.tiktok.com/@user/video/123"}'
```

**Returns:** Title, description, tags, transcription, Gemini analysis, music recognition, Drive URL

### webpage-enricher
Processes webpage URLs (articles, products, code repos)

**Endpoint:** `https://us-central1-video-processor-rhe.cloudfunctions.net/webpage-enricher`

```bash
curl -X POST $ENDPOINT \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/article"}'
```

**Returns:** Title, author, type, reading time, AI summary, AI analysis, price (if product)

## Notion Schema

Database: **Resources*** (ID: `2cf4df89-4a69-819f-941c-f3f8703ef620`)

See [docs/SCHEMA_DESIGN.md](docs/SCHEMA_DESIGN.md) for complete schema.

### Properties
| Property | Type | Purpose |
|----------|------|---------|
| Title | title | Bookmark name |
| Link | url | The URL |
| Type | select | Video, Article, Product, Code, etc. |
| Status | status | Inbox → To review → Saved |
| AI Summary | text | Auto-generated summary |
| Domain | text | Extracted from URL |
| Author | text | Content creator |
| Reading Time | number | Minutes (articles) |
| Price | number | Product price (USD) |

### Page Body Content
- AI Analysis (detailed)
- Transcript (videos)
- Visual Analysis (videos)
- Code Snippets (dev resources)
- Music Recognition (videos)

## Setup

### Prerequisites
- Google Cloud account with billing
- n8n Cloud account
- Notion workspace + integration
- API keys: Gemini, AssemblyAI, ACRCloud, OpenAI

### Deploy Cloud Functions

```bash
# video-enricher (deploys as video-downloader on GCP)
cd video-enricher
gcloud functions deploy video-downloader \
  --gen2 --runtime=python311 --region=us-central1 \
  --trigger-http --allow-unauthenticated \
  --memory=1024MB --timeout=540s \
  --set-env-vars="GEMINI_API_KEY=your-key"

# webpage-enricher
cd webpage-enricher
gcloud functions deploy webpage-enricher \
  --gen2 --runtime=python311 --region=us-central1 \
  --trigger-http --allow-unauthenticated \
  --memory=512MB --timeout=120s \
  --set-env-vars="GEMINI_API_KEY=your-key"
```

### Configure n8n
1. Import workflows from `workflows/`
2. Configure credentials (Notion, OpenAI, AssemblyAI)
3. Activate workflows

### Configure Notion Automation
Set up automatic processing for new bookmarks:

1. Open your **Resources** database in Notion
2. Click `⚡` (Automations) → **+ New automation**
3. Set trigger: **When page is added**
4. Add action: **Send webhook**
   - URL: `https://royhen.app.n8n.cloud/webhook/process-bookmark`
   - Body: Include `Link` and `id` properties
5. Save and enable

New bookmarks are now automatically enriched with AI summaries, titles, and metadata.

## Shared Utilities

The `shared/` module provides centralized validation and configuration:

| Module | Purpose |
|--------|---------|
| `title_utils.py` | Title validation, 70-char truncation at word boundaries |
| `analysis_utils.py` | Gemini analysis parsing, section icons, validation |

Section icons are defined in `shared/analysis_utils.py` and must match the n8n workflow. See [shared/README.md](shared/README.md).

## Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test categories
pytest tests/unit/test_error_contracts.py::TestSectionIcons -v    # Icon tests
pytest tests/unit/test_error_contracts.py::TestTitleLengthLimits -v  # Title tests
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, boundaries, data flows |
| [SCHEMA_DESIGN.md](docs/SCHEMA_DESIGN.md) | Notion schema design and decisions |
| [shared/README.md](shared/README.md) | Shared utilities and section icons |

## Cost Estimate

| Component | Cost per Item |
|-----------|---------------|
| Gemini 2.0 Flash | ~$0.01 |
| AssemblyAI | ~$0.005 |
| ACRCloud | ~$0.001 |
| OpenAI GPT-4 Mini | ~$0.001 |
| Cloud Function | ~$0.0004 |
| **Total (video)** | **~$0.017** |
| **Total (webpage)** | **~$0.011** |

## Infrastructure

| Resource | Details |
|----------|---------|
| GCP Project | `video-processor-rhe` |
| Region | `us-central1` |
| Cloud Functions | `video-enricher`, `webpage-enricher` |
| Storage Bucket | `video-processor-temp-rhe` |

## License

MIT License - See [LICENSE](LICENSE)

---

**Last Updated:** December 31, 2025
