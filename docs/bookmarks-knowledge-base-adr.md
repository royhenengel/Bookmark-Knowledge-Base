## ADR-004: Error Handling Flow Fixes and Resilience

**Date:** January 1, 2026

**Status:** Implemented

### Context

Testing the error notification system revealed several issues in the error handling flow:

1. Error branch bypassed `Normalize Results` node, causing missing `notionPageId`

1. `Detect URL Type` only accepted camelCase `notionPageId`, not snake_case from webhooks

1. `Set Error Status` used wrong property name ("Status" instead of "Sync Status")

1. `Set Error Status` used wrong property type ("status" instead of "select")

1. Nodes in error chain failed silently without propagating data to subsequent nodes

1. Email credentials not persisted after workflow updates

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

<!-- Table not supported -->

#### 4. Node Resilience

Made error handling nodes continue on failure to prevent cascade failures:

<!-- Table not supported -->

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

## ADR-004: Error Handling Flow Fixes and Resilience

**Date:** January 1, 2026

**Status:** Implemented

### Context

Testing the error notification system revealed several issues in the error handling flow:

1. Error branch bypassed `Normalize Results` node, causing missing `notionPageId`

1. `Detect URL Type` only accepted camelCase `notionPageId`, not snake_case from webhooks

1. `Set Error Status` used wrong property name ("Status" instead of "Sync Status")

1. `Set Error Status` used wrong property type ("status" instead of "select")

1. Nodes in error chain failed silently without propagating data to subsequent nodes

1. Email credentials not persisted after workflow updates

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

<!-- Table not supported -->

#### 4. Node Resilience

Made error handling nodes continue on failure to prevent cascade failures:

<!-- Table not supported -->

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