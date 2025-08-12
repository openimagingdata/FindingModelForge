from __future__ import annotations

from pathlib import Path
from typing import Any

from app.vite_manifest import get_vite_asset_path


def test_get_vite_asset_path_fallback_when_manifest_missing(tmp_path: Path, monkeypatch: Any) -> None:
    # Ensure the default static/.vite/manifest.json path does not exist in test tmp
    monkeypatch.chdir(tmp_path)
    # Clear cache in case previous tests populated it
    get_vite_asset_path.cache_clear()
    # Without manifest, should return default js path
    assert get_vite_asset_path("src/js/main.js") == "js/main.js"


def test_get_vite_asset_path_reads_manifest(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    # Clear cache for isolation
    get_vite_asset_path.cache_clear()
    vite_dir = Path("static/.vite")
    vite_dir.mkdir(parents=True)
    (vite_dir / "manifest.json").write_text('{"src/js/main.js": {"file": "js/main.abc123.js"}}', encoding="utf-8")

    # Should read the manifest and return the hashed file
    assert get_vite_asset_path("src/js/main.js") == "js/main.abc123.js"


def test_get_vite_asset_path_handles_malformed_manifest(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    get_vite_asset_path.cache_clear()
    vite_dir = Path("static/.vite")
    vite_dir.mkdir(parents=True)
    # Write invalid JSON
    (vite_dir / "manifest.json").write_text("{ invalid json ", encoding="utf-8")

    # Should fallback to default path when JSON parsing fails
    assert get_vite_asset_path("src/js/main.js") == "js/main.js"


def test_get_vite_asset_path_missing_entry_returns_fallback(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.chdir(tmp_path)
    get_vite_asset_path.cache_clear()
    vite_dir = Path("static/.vite")
    vite_dir.mkdir(parents=True)
    # Valid JSON but missing the requested entry
    (vite_dir / "manifest.json").write_text('{"other.js": {"file": "js/other.123.js"}}', encoding="utf-8")

    # Should fallback to default path when entry not found
    assert get_vite_asset_path("src/js/main.js") == "js/main.js"
