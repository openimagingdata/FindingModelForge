"""Form parsing and validation utilities."""

import json

from fastapi import HTTPException, status


def parse_synonyms(synonyms: str) -> list[str]:
    """Parse synonyms from JSON string.

    Args:
        synonyms: JSON array string like '["syn1", "syn2"]' or empty string

    Returns:
        List of trimmed synonym strings

    Raises:
        HTTPException: If synonyms format is invalid
    """
    if not synonyms.strip():
        return []

    try:
        synonyms_parsed = json.loads(synonyms)
        if not isinstance(synonyms_parsed, list) or not all(s and isinstance(s, str) for s in synonyms_parsed):
            raise ValueError("Synonyms must be a JSON array of strings")
        return [s.strip() for s in synonyms_parsed]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid synonyms format: {str(e)}"
        ) from e
