# Bookmarks Knowledge Base - Architecture Decision Records (ADR)

> **Last synced:** January 02, 2026 10:02 UTC

This document tracks architectural decisions made during the development of the Bookmark Knowledge Base system.

---

## ADR-001: Complete Notion Integration with Page Body Content and Error Handling

**Date:** December 27, 2025

**Status:** Implemented and deployed (commit 9dd4593)

### Context

The Bookmark_Processor n8n workflow was interrupted during initial implementation, leaving gaps in the Notion integration. The workflow could update page properties but was missing:

1. Page body content (AI Analysis, Transcript, Visual Analysis, Code Snippets, Music Recognition)
2. Sync Status property mapping
3. Error handling with notifications

### Decision

Complete the implementation by adding:

#### 1. Page Body Content Flow - 6 new nodes

| Node | Purpose |
|------|---------|
| `Get Page Blocks` | Fetch existing blocks from page |
| `Prepare Delete Blocks` | Prepare block IDs for deletion (clear before replace) |
| `Build Page Blocks` | Create Notion block objects for rich content |
| `Has Page Content?` | Conditional check for content |
| `Append Page Content` | PATCH /blocks/{id}/children API call |
| `Skip Page Content` | Pass-through when no content |

#### 2. Error Handling Branch - 6 new nodes

| Node | Purpose |
|------|---------|
| `Has Error?` | IF node routing errors vs success |
| `Set Error Status` | Sets Notion "Sync Status" property to "Error" |
| `Add Error to Page` | Adds red callout block with error details |
| `Send Error Email` | Emails royhenengel@gmail.com on failures |
| `Build Error Response` | Formats error JSON |
| `Respond with Error` | Returns 500 status |

#### 3. Property Mappings

- Added `Sync Status = "Not Synced"` to Build Notion Payload node

### Consequences

**Positive:**

- Workflow now has 22 nodes (up from 10)
- Full enrichment data now appears in Notion page body with proper formatting:
  - AI Analysis (heading + paragraph)
  - Transcript (heading + paragraph)
  - Visual Analysis (heading + paragraph)
  - Code Snippets (heading + code blocks)
  - Music Recognition (heading + bulleted list)
- Processing failures are now visible in Notion (Sync Status = Error, red callout in page)
- Email notifications alert on failures
- Sync Status property enables external sync integrations (see [notion-workspace](../../notion-workspace))

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

```
body.children[7].toggle.children[0].paragraph.rich_text[0].text.content.length
should be ≤ 2000, instead was 2360
```

This caused the workflow to fail on videos with longer transcripts (typically 2+ minutes of speech).

### Decision

Added text chunking logic to the `Build Page Blocks` node:

#### 1. New `splitText()` Helper Function

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

#### 2. Updated Block Generation

- `parseContentToBlocks()` now splits long paragraphs into multiple paragraph blocks
- `parseMarkdown()` truncates individual rich_text elements to max length
- List items are truncated to prevent overflow

### Consequences

**Positive:**

- Workflow now handles transcripts of any length
- Text splits at word boundaries for readability
- No data loss - all content is preserved across multiple blocks

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
2. Email sender showed as raw address, not a friendly name
3. Notification triggers were too narrow - some important failures were not being reported
4. AI analysis failures were silently ignored
5. Missing critical content (transcripts, prices, code snippets) went unnoticed

### Decision

#### 1. Email Configuration Updates

| Setting | Before | After |
|---------|--------|-------|
| **To** | `roy@royengel.com` | `royhenengel@gmail.com` |
| **From Display** | (none) | `LifeOS Notifications` |
| **From Address** | `notifications@royhen.app.n8n.cloud` | `royhenengel@gmail.com` (Gmail SMTP) |
| **Transport** | n8n built-in | Gmail SMTP with App Password |

#### 2. Enhanced Notification Triggers

Updated `is_error()` function in `tests/unit/test_notification_logic.py`:

| Trigger | Before | After |
|---------|--------|-------|
| HTTP 400/500 | Notify | Notify |
| Processing errors (timeout, 404, bot block) | Notify | Notify |
| AI analysis failed | **No notify** | **Notify** |
| Missing title | Notify | Notify |
| Unknown content type | Notify | Notify |
| Transcription failed | Notify | Notify |
| Video/podcast without transcript | **No notify** | **Notify** |
| Product without price | **No notify** | **Notify** |
| Code page without snippets | **No notify** | **Notify** |
| Other recoverable failures | No notify | No notify |

#### 3. Error Classification

Errors are classified into tiers:

| Tier | HTTP Status | Notification |
|------|-------------|--------------|
| **Fatal** | 400/500 | Always |
| **Processing Error** | 200 + `error` field | Always |
| **Partial Failure** | 200 + `errors` array | If critical |
| **Missing Content** | 200 | If content-type specific |
| **Success** | 200 | Never |

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

## ADR-004: Error Handling Flow Fixes and Resilience

**Date:** January 1, 2026

**Status:** Implemented

### Context

Testing the error notification system revealed several issues in the error handling flow:

1. Error branch bypassed `Normalize Results` node, causing missing `notionPageId`
2. `Detect URL Type` only accepted camelCase `notionPageId`, not snake_case from webhooks
3. `Set Error Status` used wrong property name ("Status" instead of "Sync Status")
4. `Set Error Status` used wrong property type ("status" instead of "select")
5. Nodes in error chain failed silently without propagating data to subsequent nodes
6. Email credentials not persisted after workflow updates

### Decision

#### 1. Rewired Error Flow

- Changed `Call Processor` error output to route through `Normalize Results` instead of directly to `Set Error Status`
- This ensures `notionPageId` and other normalized data is available in error branch

#### 2. Snake Case Support

Updated `Detect URL Type` node to accept both formats:
```javascript
notionPageId = body.pageId || body.notionPageId || body.notion_page_id || null;
```

#### 3. Correct Notion Property

| Setting | Before | After |
|---------|--------|-------|
| Property name | `Status` | `Sync Status` |
| Property type | `status` | `select` |

#### 4. Node Resilience

Made error handling nodes continue on failure to prevent cascade failures:

| Node | onError Setting |
|------|-----------------|
| `Set Error Status` | `continueRegularOutput` |
| `Add Error to Page` | `continueRegularOutput` |
| `Send Error Email` | `continueRegularOutput` |

#### 5. Stable Data References

Updated error nodes to reference data from `Has Error?` node instead of previous node:
```javascript
$('Has Error?').item.json.notionPageId
$('Has Error?').item.json.url
$('Has Error?').item.json.error
```

### Consequences

**Positive:**

- Error handling now completes even if individual steps fail
- Notion page gets red callout with error message
- Sync Status correctly set to "Error"
- Email notifications sent via Gmail SMTP
- Workflow accepts both camelCase and snake_case input

**Trade-offs:**

- Some error steps may silently fail (logged but not blocking)
- Email sender shows as user's Gmail (Gmail SMTP limitation)

### Related

- ADR-001: Complete Notion Integration
- ADR-003: Error Notification Rules
- n8n Workflow: `Bookmark_Processor` (ID: DJVhLZKH7YIuvGv8)

---

## ADR Template

Use this template for future ADRs:

```markdown
## ADR-XXX: [Title]

**Date:** [Date]

**Status:** [Proposed | Accepted | Deprecated | Superseded]

### Context

[What is the issue that we're seeing that is motivating this decision or change?]

### Decision

[What is the change that we're proposing and/or doing?]

### Consequences

[What becomes easier or more difficult to do because of this change?]

### Related

[Links to related documents, code, or other ADRs]
```
