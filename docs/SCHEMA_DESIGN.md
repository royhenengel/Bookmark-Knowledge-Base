# Bookmark Knowledge Base - Schema Design

## Overview

This document describes the Notion schema design for the bookmark enrichment system, including the reasoning behind each decision.

> **Note:** Raindrop.io sync is managed separately. See [notion-raindrop-sync-impl-specs.md](../../notion-workspace/docs/notion-raindrop-sync-impl-specs.md) for Raindrop schema and sync documentation.

## Design Principles

### Property vs Page Body Decision Framework

We use this framework to decide where data should live:

**Use a Property when:**
1. **You'd filter by it** - e.g., "Show all bookmarks from youtube.com"
2. **You'd sort by it** - e.g., "Longest articles first"
3. **You'd see it in list view** - Scanning bookmarks, a 1-line summary helps
4. **It's short** - Under ~200 characters, fits in a table cell
5. **It's structured** - Numbers, dates, selects, not free-form paragraphs

**Use Page Body when:**
1. **It's long** - Transcripts can be 1000+ words
2. **You only need it when deep-diving** - Not useful until reviewing that specific bookmark
3. **It needs formatting** - Code snippets need syntax highlighting, line breaks
4. **It's reference material** - You're not scanning for it, you're reading it

---

## Notion Database Schema

### Database: Resources*
**ID:** `2cf4df89-4a69-819f-941c-f3f8703ef620`

### Existing Properties (Kept)

| Property | Type | Purpose |
|----------|------|---------|
| Title | title | Bookmark name |
| Link | url | The URL |
| Type | select | Video, Podcast, Website, Document, Social media |
| Status | status | Inbox → To review → Saved |
| Description | rich_text | Manual description |
| Topics | relation | Links to Topics DB (acts as tags) |
| Project | relation | Links to Projects DB |
| Area | relation | Links to Areas DB |
| Favorite | checkbox | Quick access marker |
| Archive | checkbox | Hide from active views |
| Tasks | relation | Related tasks |
| Created time | created_time | Auto-tracked |
| Last edited | last_edited_time | Auto-tracked |

### New Properties (Added 2024-12-23)

| Property | Type | Format | Purpose | Reasoning |
|----------|------|--------|---------|-----------|
| AI Summary | rich_text | - | 2-3 sentence auto-generated summary | Short enough for list view, helps scan bookmarks quickly |
| Domain | rich_text | - | Extracted from URL (e.g., "tiktok.com") | Filter by source is a common use case |
| Author | rich_text | - | Content creator/author name | Search/filter by creator |
| Reading Time | number | number | Estimated minutes to read | Sort articles by length |
| Price | number | dollar | Product price for shopping bookmarks | Filter deals, sort by price |

> **For Raindrop sync**, additional properties (`Raindrop ID`, `Sync Status`) are required. See [notion-raindrop-sync-impl-specs.md](../../notion-workspace/docs/notion-raindrop-sync-impl-specs.md#required-notion-properties).

### Page Body Content (Not Properties)

These are stored in the page body, not as properties:

| Content | Reasoning |
|---------|-----------|
| AI Analysis | Detailed paragraphs about why the content is useful, key takeaways. Only needed when reviewing a specific bookmark. |
| Transcript | Video/audio speech-to-text. Can be 1000+ words. Reference material only. |
| Visual Analysis | Detailed breakdown of what's shown in videos. Long-form, reference only. |
| Code Snippet | Programming code from dev resources. Needs formatting, can be multi-line. |
| Music Recognition | List of recognized songs from videos. Only relevant for video bookmarks. |

---

## Content Type Detection

The system auto-detects content type based on URL patterns:

| Type | URL Patterns |
|------|--------------|
| Video | tiktok.com, youtube.com, vimeo.com, youtu.be |
| Podcast | spotify.com/episode, podcasts.apple.com, overcast.fm |
| Social media | twitter.com, x.com, instagram.com, linkedin.com/posts |
| Document | docs.google.com, notion.so, dropbox.com/paper |
| Website | Everything else |

---

## Processing Pipeline

### Video Bookmarks
1. Download video (yt-dlp primary, RapidAPI fallback)
2. Gemini 2.0 Flash analysis (full video)
3. AssemblyAI transcription
4. ACRCloud music recognition
5. GPT-4 Mini metadata generation
6. Store in Google Cloud Storage
7. Upload to Google Drive
8. Update Notion with enriched data

### Regular Bookmarks
1. Fetch page content
2. Extract metadata (title, author, publish date, reading time)
3. AI analysis and summarization
4. Detect type (article, tool, product, etc.)
5. Extract price if product page
6. Extract code snippets if dev resource
7. Update Notion with enriched data

---

## Version History

| Date | Change | Reasoning |
|------|--------|-----------|
| 2024-12-23 | Initial schema design | Base structure for bookmark sync |
| 2024-12-23 | Added 5 new properties | AI Summary, Domain, Author, Reading Time, Price |
| 2024-12-30 | Moved Raindrop sync docs | Raindrop schema/sync moved to notion-workspace repo |
| 2024-12-23 | Defined page body content | AI Analysis, Transcript, Visual Analysis, Code Snippet, Music moved to body |
