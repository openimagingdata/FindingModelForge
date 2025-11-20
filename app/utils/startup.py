"""Startup validation utilities."""

from pathlib import Path

from app.config import logger


def validate_duckdb_file(path: str | None, env_var: str, description: str) -> None:
    """Validate that a DuckDB file exists and is accessible.

    Args:
        path: Path to the DuckDB file
        env_var: Environment variable name for error messages
        description: Human-readable description of the file

    Raises:
        RuntimeError: If the file doesn't exist or isn't a file
    """
    if not path:
        return

    file_path = Path(path)
    logger.info(f"  {description} path: {file_path}")

    if not file_path.exists():
        raise RuntimeError(
            f"DuckDB file not found: {file_path}\nSet {env_var} to correct location or ensure file exists"
        )

    if not file_path.is_file():
        raise RuntimeError(f"DuckDB path is not a file: {file_path}")

    size_mb = file_path.stat().st_size / 1024 / 1024
    logger.info(f"  ✓ {description} found ({size_mb:.1f} MB)")
