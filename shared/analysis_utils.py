"""
Gemini Analysis utilities for Bookmark Knowledge Base.

Parses and validates the structured analysis from Gemini video analysis.
All required sections must be present and non-empty.
"""

import re
from typing import Dict, List, Optional, Tuple

# Section icons - must match n8n workflow sectionIcons
SECTION_ICONS = {
    'Visual Content': '👁️',
    'Audio Content': '🔊',
    'Style & Production': '🎬',
    'Mood & Tone': '🎭',
    'Key Messages': '💡',
    'Content Category': '📁',
    'Transcript': '📝',
}

# Required sections in Gemini video analysis (order matters for prompt)
REQUIRED_ANALYSIS_SECTIONS = [
    'Visual Content',
    'Audio Content',
    'Style & Production',
    'Mood & Tone',
    'Key Messages',
    'Content Category',
]


def get_section_icon(section_name: str) -> str:
    """Get the icon for a section name."""
    return SECTION_ICONS.get(section_name, '📌')


def _strip_icon(text: str) -> str:
    """Strip emoji icons from section name."""
    # Remove common emoji patterns from start of text
    # This handles: "👁️ Visual Content" -> "Visual Content"
    if not text:
        return text
    # Strip leading emoji (including variation selectors like \ufe0f) and whitespace
    # Emoji ranges: various emoji blocks + variation selectors
    cleaned = re.sub(
        r'^[\U0001F300-\U0001F9FF\U00002600-\U000027BF\uFE00-\uFE0F\U0001F1E0-\U0001F1FF\s]+',
        '', text
    )
    return cleaned.strip()


def parse_gemini_analysis(analysis_text: str) -> Dict[str, str]:
    """
    Parse Gemini analysis text into structured sections.

    Expects markdown format with numbered headers like:
    1. **👁️ Visual Content**
    2. **🔊 Audio Content**

    Also handles legacy format with colons:
    1. **Visual Content**: content on same line...

    Args:
        analysis_text: Raw markdown text from Gemini

    Returns:
        Dict mapping section names to their content (icons stripped from names)
    """
    if not analysis_text:
        return {}

    sections = {}

    # Split by numbered lines and process
    lines = analysis_text.split('\n')
    current_section = None
    current_content = []

    for line in lines:
        # Match patterns:
        # - "1. **👁️ Visual Content**" (new format, content on next line)
        # - "1. **Visual Content**: content here" (legacy format, content on same line)
        # - "1. **Visual Content**:" (legacy format, content on next line)
        header_match = re.match(
            r'^\d+\.\s*\*\*([^*]+)\*\*[:\s]*(.*?)$',
            line.strip()
        )

        if header_match:
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()

            current_section = _strip_icon(header_match.group(1).strip())
            # Check if there's content on the same line
            same_line_content = header_match.group(2).strip()
            current_content = [same_line_content] if same_line_content else []
        elif current_section:
            current_content.append(line)

    # Don't forget the last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    # If no sections found, try ## heading format
    if not sections:
        for line in lines:
            heading_match = re.match(r'^##\s*(.+?)\s*$', line.strip())
            if heading_match:
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = _strip_icon(heading_match.group(1).strip())
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

    return sections


def validate_analysis_sections(
    analysis_text: str,
    required_sections: List[str] = None,
    include_transcript: bool = False
) -> Dict:
    """
    Validate that Gemini analysis contains all required sections with content.

    Args:
        analysis_text: Raw analysis text from Gemini
        required_sections: List of section names to require (uses defaults if None)
        include_transcript: If True, also requires transcript section

    Returns:
        Dict with:
            valid: bool - True if all required sections are present and non-empty
            sections: dict - Parsed sections with their content
            missing: list - Section names that are missing
            empty: list - Section names that are present but empty
            errors: list - Error messages
    """
    if required_sections is None:
        required_sections = REQUIRED_ANALYSIS_SECTIONS.copy()

    if include_transcript:
        required_sections = required_sections + ['Transcript']

    result = {
        'valid': True,
        'sections': {},
        'missing': [],
        'empty': [],
        'errors': []
    }

    if not analysis_text:
        result['valid'] = False
        result['errors'].append('Analysis text is missing or empty')
        result['missing'] = required_sections
        return result

    # Parse the analysis
    sections = parse_gemini_analysis(analysis_text)
    result['sections'] = sections

    # Check for each required section
    for section_name in required_sections:
        # Try exact match first
        content = sections.get(section_name)

        # Try case-insensitive match
        if content is None:
            for key, value in sections.items():
                if key.lower() == section_name.lower():
                    content = value
                    break

        # Try partial match (e.g., "Mood & Tone" matches "Mood and Tone")
        if content is None:
            section_words = set(re.findall(r'\w+', section_name.lower()))
            for key, value in sections.items():
                key_words = set(re.findall(r'\w+', key.lower()))
                if section_words == key_words:
                    content = value
                    break

        if content is None:
            result['missing'].append(section_name)
            result['errors'].append(f"Missing required section: {section_name}")
            result['valid'] = False
        elif not content.strip():
            result['empty'].append(section_name)
            result['errors'].append(f"Section is empty: {section_name}")
            result['valid'] = False

    return result


def validate_transcription(transcription_result: Optional[Dict]) -> Dict:
    """
    Validate that transcription result contains required fields.

    Args:
        transcription_result: Result from transcribe_audio function

    Returns:
        Dict with:
            valid: bool
            errors: list
    """
    result = {
        'valid': True,
        'errors': []
    }

    if transcription_result is None:
        result['valid'] = False
        result['errors'].append('Transcription result is missing')
        return result

    if 'error' in transcription_result and transcription_result['error']:
        result['valid'] = False
        result['errors'].append(f"Transcription error: {transcription_result['error']}")
        return result

    text = transcription_result.get('text')
    if not text or not text.strip():
        result['valid'] = False
        result['errors'].append('Transcript text is empty')

    return result


def validate_video_enrichment(response: Dict) -> Dict:
    """
    Validate complete video enrichment response.

    Checks:
    - gemini_analysis contains all required sections
    - transcription (if present) has non-empty text
    - All required metadata fields are present

    Args:
        response: Full response from video enricher

    Returns:
        Dict with:
            valid: bool
            errors: list - All validation errors
            analysis_validation: dict - Analysis section validation
            transcription_validation: dict - Transcription validation
    """
    result = {
        'valid': True,
        'errors': [],
        'analysis_validation': None,
        'transcription_validation': None
    }

    # Validate Gemini analysis
    gemini_result = response.get('gemini_analysis', {})
    if gemini_result:
        analysis_text = gemini_result.get('analysis', '')
        if gemini_result.get('error'):
            result['valid'] = False
            result['errors'].append(f"Gemini analysis error: {gemini_result['error']}")
        else:
            analysis_validation = validate_analysis_sections(analysis_text)
            result['analysis_validation'] = analysis_validation
            if not analysis_validation['valid']:
                result['valid'] = False
                result['errors'].extend(analysis_validation['errors'])

    # Validate transcription if present
    transcription = response.get('transcription')
    if transcription:
        transcription_validation = validate_transcription(transcription)
        result['transcription_validation'] = transcription_validation
        if not transcription_validation['valid']:
            result['valid'] = False
            result['errors'].extend(transcription_validation['errors'])

    return result
