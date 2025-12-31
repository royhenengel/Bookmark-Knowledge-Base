"""
Title processing utilities for Bookmark Knowledge Base.

All titles in the system are limited to 70 characters maximum.
Titles exceeding this limit must be:
1. Truncated at word boundaries (not mid-word)
2. Flagged as errors for notification
"""

import re
from typing import Tuple

# Global title limit for all content types
MAX_TITLE_LENGTH = 70


def truncate_title(title: str, max_length: int = MAX_TITLE_LENGTH) -> Tuple[str, bool]:
    """
    Truncate title at word boundary, not mid-word.

    Args:
        title: The title to truncate
        max_length: Maximum length (default 70)

    Returns:
        Tuple of (truncated_title, was_truncated)

    Examples:
        >>> truncate_title("Hello World", 70)
        ('Hello World', False)

        >>> truncate_title("This is a very long title that exceeds the limit", 20)
        ('This is a very long', True)
    """
    if not title:
        return ('', False)

    # Clean whitespace
    title = ' '.join(title.split())

    # If already short enough, return as-is
    if len(title) <= max_length:
        return (title, False)

    # Find the last space before the limit
    truncated = title[:max_length]
    last_space = truncated.rfind(' ')

    # If no space found (single long word), truncate at limit with ellipsis
    if last_space == -1:
        return (title[:max_length-3] + '...', True)

    # Truncate at word boundary
    return (truncated[:last_space].rstrip(), True)


def validate_title(title: str) -> dict:
    """
    Validate title for quality issues.

    Returns dict with:
        valid: bool - True if title passes all checks
        errors: list - List of error messages
        warnings: list - List of warning messages
    """
    errors = []
    warnings = []

    if not title:
        errors.append("Title is missing or empty")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Check for whitespace-only
    if not title.strip():
        errors.append("Title contains only whitespace")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Check length
    if len(title) > MAX_TITLE_LENGTH:
        errors.append(f"Title exceeds {MAX_TITLE_LENGTH} character limit ({len(title)} chars)")

    # Check for null bytes
    if '\x00' in title:
        errors.append("Title contains null bytes (likely encoding issue)")

    # Check for only special characters (no alphanumeric)
    alphanumeric = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    if not alphanumeric.strip():
        errors.append("Title contains no alphanumeric characters")

    # Check for suspicious patterns
    if len(title) > 200:
        warnings.append("Title is unusually long (>200 chars) - may indicate scraping issue")

    # Check for truncated words (ends with partial word)
    if title and title[-1].isalnum() and len(title) >= MAX_TITLE_LENGTH:
        # Could be mid-word truncation
        warnings.append("Title may have been truncated mid-word")

    # Check for incomplete sentence (ends with conjunction/preposition)
    incomplete_endings = [' and', ' or', ' the', ' a', ' an', ' to', ' for', ' with', ' in', ' on', ' at', ' by']
    lower_title = title.lower()
    for ending in incomplete_endings:
        if lower_title.endswith(ending):
            warnings.append(f"Title ends with incomplete word '{ending.strip()}'")
            break

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def is_title_valid(title: str) -> bool:
    """Simple check if title is valid (no errors)."""
    return validate_title(title)['valid']


def sanitize_title(title: str) -> str:
    """
    Sanitize title for safe use in filenames and displays.

    - Removes null bytes
    - Removes control characters
    - Normalizes whitespace
    - Keeps letters, numbers, spaces, and common punctuation
    """
    if not title:
        return ''

    # Remove null bytes and control characters
    title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', title)

    # Keep only safe characters
    title = ''.join(c for c in title if c.isalnum() or c.isspace() or c in '.,!?-:;\'\"()[]')

    # Normalize whitespace
    title = ' '.join(title.split())

    return title


def validate_title_quality(title: str) -> dict:
    """
    Validate title quality for clarity and readability.

    Checks for:
    - Incomplete sentences (cut off mid-word)
    - Repeated words
    - All caps (shouting)
    - No spaces (concatenated words)
    - Suspicious patterns (garbage text)

    Returns dict with:
        quality_score: float (0-1, where 1 is perfect)
        issues: list of issue descriptions
        is_acceptable: bool (True if quality_score >= 0.7)
    """
    issues = []
    score = 1.0

    if not title or not title.strip():
        return {'quality_score': 0, 'issues': ['Title is empty'], 'is_acceptable': False}

    title = title.strip()

    # Check for all caps
    if title.isupper() and len(title) > 5:
        issues.append("Title is all uppercase (considered shouting)")
        score -= 0.2

    # Check for no spaces (concatenated words likely)
    if len(title) > 20 and ' ' not in title:
        issues.append("Title has no spaces - may be concatenated words")
        score -= 0.3

    # Check for repeated words
    words = title.lower().split()
    if len(words) > 1:
        for i in range(len(words) - 1):
            if words[i] == words[i + 1]:
                issues.append(f"Repeated word: '{words[i]}'")
                score -= 0.1
                break

    # Check for incomplete word at end (ends with lowercase letter after truncation)
    if len(title) >= MAX_TITLE_LENGTH - 5:
        last_word = title.split()[-1] if title.split() else ''
        # Common word endings that suggest complete words
        complete_endings = ('ing', 'tion', 'ment', 'ness', 'able', 'ible', 'ly', 'ed', 'er', 'est', 'ful', 'less')
        if last_word and not last_word.endswith(complete_endings) and last_word[-1].islower():
            # Could be truncated - flag as warning
            issues.append("Title may end with incomplete word")
            score -= 0.15

    # Check for suspicious character patterns (garbage text indicators)
    garbage_patterns = [
        r'[a-z]{15,}',  # 15+ consecutive lowercase letters (no spaces)
        r'(.)\1{4,}',    # Same character repeated 5+ times
        r'\d{10,}',      # 10+ consecutive digits
    ]
    for pattern in garbage_patterns:
        if re.search(pattern, title.lower()):
            issues.append("Title contains suspicious character patterns")
            score -= 0.3
            break

    # Check for very short title
    if len(title) < 5:
        issues.append("Title is very short (less than 5 characters)")
        score -= 0.2

    # Ensure score is in valid range
    score = max(0, min(1, score))

    return {
        'quality_score': round(score, 2),
        'issues': issues,
        'is_acceptable': score >= 0.7
    }


def validate_title_with_ai(title: str, use_llm: bool = False) -> dict:
    """
    Validate title using AI analysis.

    Args:
        title: The title to validate
        use_llm: If True, uses external LLM for deeper analysis (requires API key)

    Returns:
        dict with validation results including spelling/grammar issues
    """
    # First, run pattern-based validation
    result = validate_title_quality(title)

    if not use_llm:
        return result

    # LLM-based validation would go here
    # This is a placeholder for future implementation
    # Could use Gemini, OpenAI, etc. to check:
    # - Spelling errors
    # - Grammar issues
    # - Clarity/readability
    # - Whether title makes sense

    result['llm_validated'] = False
    result['llm_notes'] = 'LLM validation not yet implemented'

    return result
