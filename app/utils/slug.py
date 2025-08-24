"""Slug utilities for URL generation and normalization."""


def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug.

    Args:
        name: The name to convert to a slug

    Returns:
        URL-friendly slug with spaces and underscores replaced by hyphens

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Test_Name")
        'test-name'
        >>> slugify("Mixed Test_Name")
        'mixed-test-name'
    """
    return name.lower().replace(" ", "-").replace("_", "-")


def generate_slug_variants(slug: str) -> list[str]:
    """Generate lookup variants for slug matching.

    This function creates different variations of a slug to handle cases where
    the same content might be referenced with different separator conventions
    (spaces, hyphens, underscores).

    Args:
        slug: The original slug to generate variants for

    Returns:
        List of slug variants ordered by preference for lookup

    Examples:
        >>> generate_slug_variants("hello-world")
        ['hello world', 'hello-world', 'hello_world']
        >>> generate_slug_variants("test_name")
        ['test name', 'test_name', 'test-name']
    """
    raw_slug = (slug or "").strip().lower()
    variant_spaces = raw_slug.replace("-", " ").replace("_", " ")
    variant_hyphen = raw_slug.replace("_", "-")
    variant_underscore = raw_slug.replace("-", "_")

    candidates: list[str] = []
    for candidate in (variant_spaces, raw_slug, variant_hyphen, variant_underscore):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    return candidates


def normalize_for_cache(slug: str) -> str:
    """Normalize a slug for consistent cache key generation.

    Uses space-normalized variant as the canonical cache key to remain compatible
    with existing expectations while ensuring consistent keys across different
    slug input formats.

    Args:
        slug: The slug to normalize

    Returns:
        Normalized slug suitable for use as a cache key

    Examples:
        >>> normalize_for_cache("hello-world")
        'hello world'
        >>> normalize_for_cache("test_name")
        'test name'
        >>> normalize_for_cache("Mixed-Test_Name")
        'mixed test name'
    """
    raw_slug = (slug or "").strip().lower()
    return raw_slug.replace("-", " ").replace("_", " ")
