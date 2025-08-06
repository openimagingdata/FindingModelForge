"""Utility to read Vite manifest for asset paths."""

import json
from functools import lru_cache
from pathlib import Path

from app.config import logger


@lru_cache(maxsize=1)
def get_vite_asset_path(entry_name: str = "src/js/main.js") -> str:
    """
    Get the built asset path for a Vite entry point.

    Args:
        entry_name: The original source file name (e.g., "src/js/main.js")

    Returns:
        The built asset path (e.g., "js/main.abc123.js") or fallback
    """
    manifest_path = Path("static/.vite/manifest.json")

    try:
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

            entry = manifest.get(entry_name)
            if entry and "file" in entry:
                return str(entry["file"])

        # Fallback if manifest doesn't exist or entry not found
        return "js/main.js"

    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Error reading Vite manifest: {e}")
        return "js/main.js"
