# Shared Utilities

Centralized validation and configuration utilities used by both Cloud Functions (`video-enricher`, `webpage-enricher`) and n8n workflows.

## Purpose

This module ensures consistency between:
- **Cloud Functions** - Python code that processes content
- **n8n workflows** - JavaScript code that formats and routes data
- **Tests** - Validate contracts are maintained

## Modules

### title_utils.py

Title validation and sanitization with a **70-character limit**.

```python
from shared import truncate_title, validate_title, sanitize_title

# Truncate at word boundary
title, was_truncated = truncate_title("Very long title...", max_length=70)

# Validate title quality
result = validate_title(title)
# {'valid': True, 'errors': [], 'warnings': []}

# Sanitize for safe use
clean = sanitize_title("Title with\x00nulls")
```

| Function | Purpose |
|----------|---------|
| `truncate_title(title, max_length)` | Truncate at word boundary, returns (title, was_truncated) |
| `validate_title(title)` | Check for errors (empty, too long, null bytes) |
| `is_title_valid(title)` | Simple bool check |
| `sanitize_title(title)` | Remove unsafe characters |
| `validate_title_quality(title)` | Quality scoring (0-1) for issues like all-caps, no spaces |

### analysis_utils.py

Gemini video analysis parsing and validation.

```python
from shared import (
    SECTION_ICONS,
    REQUIRED_ANALYSIS_SECTIONS,
    parse_gemini_analysis,
    validate_analysis_sections,
)

# Parse Gemini response into sections
sections = parse_gemini_analysis(gemini_text)
# {'Visual Content': '...', 'Audio Content': '...', ...}

# Validate all required sections are present
result = validate_analysis_sections(gemini_text)
# {'valid': True, 'sections': {...}, 'missing': [], 'empty': [], 'errors': []}
```

## Section Icons

**Critical:** These icons must match the `sectionIcons` object in the n8n workflow (`Bookmark_Processor.json`).

```python
SECTION_ICONS = {
    'Visual Content': '👁️',
    'Audio Content': '🔊',
    'Style & Production': '🎬',
    'Mood & Tone': '🎭',
    'Key Messages': '💡',
    'Content Category': '📁',
    'Transcript': '📝',
}
```

The Gemini prompt in `video-enricher/main.py` uses these icons in section headers:

```
1. **👁️ Visual Content**
Describe what you see...

2. **🔊 Audio Content**
Describe the audio...
```

The n8n workflow uses the same icons when formatting content for Notion page body.

### Keeping Icons in Sync

If icons need to change:

1. Update `SECTION_ICONS` in `shared/analysis_utils.py`
2. Update Gemini prompt in `video-enricher/main.py`
3. Update `sectionIcons` in n8n workflow `Build Page Blocks` node
4. Run tests: `pytest tests/unit/test_error_contracts.py::TestSectionIcons -v`

Tests verify the icons match expected values:

```python
def test_icons_match_n8n_workflow(self):
    """Icons must match the sectionIcons in the n8n workflow."""
    n8n_icons = {
        'Visual Content': '👁️',
        'Audio Content': '🔊',
        # ...
    }
    for section, expected_icon in n8n_icons.items():
        assert SECTION_ICONS.get(section) == expected_icon
```

## Required Analysis Sections

The video enricher requires these 6 sections in every Gemini analysis:

```python
REQUIRED_ANALYSIS_SECTIONS = [
    'Visual Content',
    'Audio Content',
    'Style & Production',
    'Mood & Tone',
    'Key Messages',
    'Content Category',
]
```

Plus optionally: `Transcript` (from transcription, not Gemini)

## Parser Formats

`parse_gemini_analysis()` handles multiple formats for backward compatibility:

**New format (with icons, no colon):**
```markdown
1. **👁️ Visual Content**
The video shows a person cooking...

2. **🔊 Audio Content**
Background music plays throughout...
```

**Legacy format (no icons, with colon):**
```markdown
1. **Visual Content**: The video shows a person cooking...

2. **Audio Content**: Background music plays throughout...
```

Both formats parse to the same dict with icon-free keys:
```python
{
    'Visual Content': 'The video shows...',
    'Audio Content': 'Background music...',
}
```

## Testing

```bash
# Run all shared utility tests
pytest tests/unit/test_error_contracts.py -v

# Run only section icon tests
pytest tests/unit/test_error_contracts.py::TestSectionIcons -v

# Run only title validation tests
pytest tests/unit/test_error_contracts.py::TestTitleLengthLimits -v
pytest tests/unit/test_error_contracts.py::TestTitleQualityValidation -v
```

## Usage in Cloud Functions

Both Cloud Functions import from the shared module:

```python
# video-enricher/main.py
from shared.analysis_utils import (
    validate_video_enrichment,
    REQUIRED_ANALYSIS_SECTIONS,
    SECTION_ICONS,
)

# webpage-enricher/main.py
from shared.title_utils import truncate_title, validate_title
```

## Related

- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design
- [ADR.md](../docs/ADR.md) - Architecture decisions
- Test file: `tests/unit/test_error_contracts.py`
