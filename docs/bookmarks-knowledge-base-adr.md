> **Last synced:** January 02, 2026 16:56 UTC

This document tracks architectural decisions made during the development of the Bookmark Knowledge Base system.

---

## ADR-001: Complete Notion Integration with Page Body Content and Error Handling

**Date:** December 27, 2025

**Status:** Implemented and deployed (commit 9dd4593)

### Context

The Bookmark_Processor n8n workflow was interrupted during initial implementation, leaving gaps in the Notion integration. The workflow could update page properties but was missing:

1. Page body content (AI Analysis, Transcript, Visual Analysis, Code Snippets, Music Recognition)

1. Sync Status property mapping

1. Error handling with notifications

### Decision

Complete the implementation by adding:

### 1. Page Body Content Flow – 6 new nodes

<!-- Table not supported -->

### 2. Error Handling Branch – 6 new nodes

<!-- Table not supported -->

### 3. Property Mappings

- Added `Sync Status = "Not Synced"` to Build Notion Payload node

### Consequences

**Positive:**

- Workflow now has 22 nodes (up from 10)

- Full enrichment data now appears in Notion page body with proper formatting:

  – AI Analysis (heading + paragraph)

  – Transcript (heading + paragraph)

  – Visual Analysis (heading + paragraph)

  – Code Snippets (heading + code blocks)

  – Music Recognition (heading + bulleted list)

- Processing failures are now visible in Notion (Sync Status = Error, red callout in page)

- Email notifications alert on failures

- Sync Status property enables external sync integrations (see notion-workspace)

**Trade-offs:**

- Increased workflow complexity (21 vs 10 nodes)

- Additional API calls per bookmark (get blocks, delete blocks, append blocks)

### Related

- Architecture: `/docs/ARCHITECTURE.md`

- Schema: `/docs/SCHEMA_DESIGN.md`

- n8n Workflow: `Bookmark_Processor`

---

## ADR-002: Notion API Text Length Limit Handling

**Date:** December 28, 2025

**Status:** Implemented

### Context

The Notion API enforces a **2000 character limit** per `rich_text` content block. When processing video transcripts or long-form content, the `Build Page Blocks` node was generating blocks that exceeded this limit, causing API errors:

```plain text
body.children[7].toggle.children[0].paragraph.rich_text[0].text.content.length
should be ≤ 2000, instead was 2360
```

This caused the workflow to fail on videos with longer transcripts (typically 2+ minutes of speech).

### Decision

Added text chunking logic to the `Build Page Blocks` node:

### 1. New `splitText()` Helper Function

```javascript
function splitText(text, maxLength = 2000) {
  if (!text || text.length <= maxLength) return [text];

  const chunks = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining);
      break;
    }

    // Find last space before limit (word boundary)
    let splitAt = remaining.lastIndexOf(' ', maxLength);
    if (splitAt === -1 || splitAt < maxLength / 2) {
      splitAt = maxLength; // Force split if no good space
    }

    chunks.push(remaining.substring(0, splitAt));
    remaining = remaining.substring(splitAt).trim();
  }

  return chunks;
}
```

### 2. Updated Block Generation

- `parseContentToBlocks()` now splits long paragraphs into multiple paragraph blocks

- `parseMarkdown()` truncates individual rich_text elements to max length

- List items are truncated to prevent overflow

### Consequences

**Positive:**

- Workflow now handles transcripts of any length

- Text splits at word boundaries for readability

- No data loss – all content is preserved across multiple blocks

**Trade-offs:**

- Long transcripts appear as multiple paragraphs within toggles (visually acceptable)

- Slightly more blocks per page for long content

### Related

- ADR-001: Complete Notion Integration

- Notion API Docs: [Block limits](https://developers.notion.com/reference/request-limits#limits-for-property-values)

---

## ADR-003: Error Notification Rules and Email Configuration

**Date:** January 1, 2026

**Status:** Implemented

### Context

The error notification system needed refinement:

1. Email was configured to send to a non-existent address (`roy@royengel.com`)

1. Email sender showed as raw address, not a friendly name

1. Notification triggers were too narrow – some important failures were not being reported

1. AI analysis failures were silently ignored

1. Missing critical content (transcripts, prices, code snippets) went unnoticed

### Decision

### 1. Email Configuration Updates

<!-- Table not supported -->

### 2. Enhanced Notification Triggers

Updated `is_error()` function in `tests/unit/test_notification_logic.py`:

<!-- Table not supported -->

### 3. Error Classification

Errors are classified into tiers:

<!-- Table not supported -->

### Consequences

**Positive:**

- Notifications now arrive at working email address

- Email clearly shows "LifeOS" as sender

- AI failures are now tracked and reported

- Content-specific failures (no transcript, no price, no code) are caught

- Better visibility into processing quality

**Trade-offs:**

- May generate more notifications initially (expected during tuning)

- Some "false positives" for content that genuinely has no transcript/price/code

### Related

- ADR-001: Complete Notion Integration (original error handling)

- n8n Workflow: `Bookmark_Processor` (Send Error Email node)

- Test file: `tests/unit/test_notification_logic.py`

---