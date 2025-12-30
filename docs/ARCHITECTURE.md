# Bookmark Knowledge Base - System Architecture

## Overview

This document defines the system architecture, component boundaries, and responsibilities for the Bookmark Knowledge Base system.

---

## Design Philosophy

### Separation of Concerns

Each system has a **single responsibility**:

| System | Responsibility | NOT Responsible For |
|--------|----------------|---------------------|
| **Cloud Functions** | Processing & Intelligence | Data storage, orchestration |
| **n8n** | Orchestration & Data Movement | Business logic, heavy processing |
| **Notion** | Rich Data Storage & UI | Processing, external integrations |
| **Google Cloud Storage** | Media Storage | Processing, metadata |

> **Note:** Raindrop.io sync is managed separately in [notion-workspace](../../notion-workspace). See [notion-raindrop-sync-impl-specs.md](../../notion-workspace/docs/notion-raindrop-sync-impl-specs.md).

### Why This Matters

1. **Testability** - Each component can be tested in isolation
2. **Scalability** - Scale processing independently from orchestration
3. **Maintainability** - Changes to one system don't cascade
4. **Debuggability** - Clear boundaries make issues easier to trace
5. **Replaceability** - Swap components without rewriting everything

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌──────────────────┐                                │
│                         │      Notion      │                                │
│                         │   (Resources)    │                                │
│                         │                  │                                │
│                         │ • Rich UI        │                                │
│                         │ • Relations      │                                │
│                         │ • Views          │                                │
│                         └────────┬─────────┘                                │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │ Webhook on new bookmark
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌──────────────────┐                                │
│                         │       n8n        │                                │
│                         │                  │                                │
│                         │ • Triggers       │                                │
│                         │ • Routing        │                                │
│                         │ • Data mapping   │                                │
│                         │ • Error handling │                                │
│                         │ • Retries        │                                │
│                         └────────┬─────────┘                                │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROCESSING LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │   video-enricher    │              │  webpage-enricher   │              │
│  │   (Cloud Function)  │              │  (Cloud Function)   │              │
│  │                     │              │                     │              │
│  │ • Download video    │              │ • Fetch webpage     │              │
│  │ • Gemini analysis   │              │ • Extract metadata  │              │
│  │ • Transcription     │              │ • AI summary        │              │
│  │ • Music recognition │              │ • Price extraction  │              │
│  │ • Store media       │              │ • Code extraction   │              │
│  └─────────────────────┘              └─────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STORAGE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────┐              ┌─────────────────────┐              │
│  │  Google Cloud       │              │   Google Drive      │              │
│  │  Storage            │              │                     │              │
│  │                     │              │ • User-accessible   │              │
│  │ • Temporary media   │              │   video archive     │              │
│  │ • Processing cache  │              │                     │              │
│  └─────────────────────┘              └─────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### Cloud Functions (Processing Layer)

**Purpose:** Heavy computation, AI analysis, external API calls

| Function | Input | Output | Responsibilities |
|----------|-------|--------|------------------|
| `video-enricher` | Video URL | Enriched JSON + stored media | Download, analyze, transcribe, recognize music |
| `webpage-enricher` | Web URL | Enriched JSON | Fetch, extract, summarize, detect type |

**Rules:**
- ✅ DO: AI analysis, data extraction, API calls to processing services
- ✅ DO: Store media to GCS/Drive
- ✅ DO: Return structured JSON with all extracted data
- ❌ DON'T: Write to Notion directly
- ❌ DON'T: Make decisions about what to sync where
- ❌ DON'T: Handle retries or error recovery (that's n8n's job)

**Interface Contract:**

```typescript
// Input (both functions)
interface ProcessingRequest {
  url: string;
  options?: {
    skip_ai?: boolean;
    skip_media_storage?: boolean;
  };
}

// Output: video-enricher
interface VideoProcessingResult {
  url: string;
  title: string;
  author: string;
  domain: string;
  type: "video";
  duration: number;
  gemini_analysis: {
    analysis: string;
    model: string;
  };
  transcription: string;
  music: {
    recognized_songs: Song[];
    recognition_status: string;
  };
  cloud_storage: {
    video_url: string;
    audio_url: string;
  };
  google_drive: {
    file_id: string;
    file_url: string;
  };
}

// Output: webpage-enricher
interface WebpageProcessingResult {
  url: string;
  title: string;
  author: string | null;
  domain: string;
  type: "article" | "product" | "tool" | "code" | "social" | "other";
  ai_summary: string;
  ai_analysis: string;
  reading_time: number | null;
  price: number | null;
  currency: string | null;
  code_snippets: string[];
  main_image: string | null;
  published_date: string | null;
}
```

---

### n8n (Orchestration Layer)

**Purpose:** Workflow automation, data routing, sync coordination

**Rules:**
- ✅ DO: Trigger workflows on events (webhook, schedule, database change)
- ✅ DO: Route requests to appropriate Cloud Function based on URL type
- ✅ DO: Handle errors, retries, notifications
- ✅ DO: Write enriched data to Notion
- ❌ DON'T: Perform heavy computation or AI calls
- ❌ DON'T: Store state beyond workflow execution
- ❌ DON'T: Implement business logic (just routing logic)

**Workflows:**

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `process-bookmark` | Notion webhook | Route to video-enricher or webpage-enricher |
| `video-processor` | Called by process-bookmark | Video-specific processing (ACRCloud, Drive) |
| `backlog-processor` | Manual/scheduled | Batch process unprocessed bookmarks |

---

### Notion (Primary Storage)

**Purpose:** Rich data storage, user interface, relations

**Rules:**
- ✅ IS: Source of truth for bookmark metadata
- ✅ IS: Primary user interface for browsing/organizing
- ✅ HAS: Rich properties, relations, rollups, views
- ❌ ISN'T: Processing engine
- ❌ ISN'T: Integration hub

**Data Owned:**
- All bookmark properties (title, type, status, etc.)
- Relations to Topics, Projects, Areas
- AI-generated content (summary, analysis, transcript)
- Page body content

---

## Data Flow Patterns

### Pattern 1: New Bookmark from Notion

```
User adds URL to Notion
        │
        ▼
n8n detects new entry (webhook)
        │
        ▼
n8n checks URL type
        │
        ├─► Video URL ──► video-enricher Cloud Function
        │                        │
        │                        ▼
        │                 Returns enriched JSON
        │                        │
        └─► Web URL ────► webpage-enricher Cloud Function
                                 │
                                 ▼
                          Returns enriched JSON
                                 │
                                 ▼
                    n8n updates Notion with enriched data
```

### Pattern 2: Backlog Processing

```
Scheduled trigger (or manual)
        │
        ▼
n8n queries Notion for Status = "Inbox"
        │
        ▼
For each unprocessed bookmark:
        │
        ├─► Route to appropriate Cloud Function
        │
        └─► Update Notion with results
        │
        ▼
Rate limit: X bookmarks per batch
```

---

## Error Handling Strategy

### Cloud Functions
- Return error in JSON response, don't throw
- Include error details for debugging
- Partial results are OK (e.g., video downloaded but transcription failed)

```json
{
  "url": "https://...",
  "title": "Extracted title",
  "error": {
    "stage": "transcription",
    "message": "AssemblyAI rate limit exceeded",
    "recoverable": true
  }
}
```

### n8n
- Catch errors from Cloud Functions
- Set bookmark Status = "Error" in Notion
- Log error details
- Retry recoverable errors (with backoff)
- Notify on persistent failures

---

## API Keys & Credentials

| Service | Used By | Storage |
|---------|---------|---------|
| Gemini API | video-enricher | Cloud Function env var |
| AssemblyAI | n8n workflow | n8n credentials |
| ACRCloud | n8n workflow | n8n credentials |
| OpenAI | n8n workflow | n8n credentials |
| Notion | n8n workflow | n8n credentials |
| Google Cloud | video-enricher, webpage-enricher | Service account |

**Rule:** API keys never hardcoded. Always environment variables or credential stores.

---

## Scaling Considerations

### Current (MVP)
- Single Cloud Function instances
- n8n cloud (free tier limits)
- Sequential processing

### Future (if needed)
- Cloud Function concurrency scaling
- n8n self-hosted for higher throughput
- Batch processing with queues
- Caching layer for repeated URLs

---

## Decision Log

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2024-12-23 | Separate Cloud Functions for video vs webpage | Different processing needs, independent scaling, clearer boundaries |
| 2024-12-23 | n8n for orchestration only | Keep logic in testable Cloud Functions, n8n for routing/mapping |
| 2024-12-23 | Notion as source of truth | Richer schema, better UI, relations support |
| 2024-12-23 | Cloud Functions don't write to Notion | Single responsibility - processing only returns data |
| 2024-12-30 | Moved Raindrop sync to notion-workspace | Separation of concerns - sync managed separately |
| 2025-12-27 | Complete Notion integration with page body content | Full enrichment data in page body, error handling with notifications (see ADR-001) |

---

## Version History

| Date | Change |
|------|--------|
| 2024-12-23 | Initial architecture document |
| 2024-12-23 | Defined component boundaries and responsibilities |
| 2024-12-23 | Added data flow patterns |
| 2024-12-23 | Added error handling strategy |
| 2025-12-27 | Added ADR-001: Complete Notion integration with page body content and error handling |
