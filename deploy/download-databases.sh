#!/bin/bash
set -e

[ $# -eq 1 ] || { echo "Usage: $0 <data-dir>"; exit 1; }

DATA_DIR="$1"
MANIFEST="$DATA_DIR/manifest.json"

mkdir -p "$DATA_DIR"
curl -sf https://findingmodelsdata.fly.storage.tigris.dev/manifest.json -o "$MANIFEST"

download_db() {
    local key=$1 file="$DATA_DIR/$1.duckdb"
    local url=$(jq -r ".databases.$key.url" "$MANIFEST")
    local hash=$(jq -r ".databases.$key.hash" "$MANIFEST")

    curl -f "$url" -o "$file"
    [ "sha256:$(shasum -a 256 "$file" | awk '{print $1}')" = "$hash" ] || { echo "Hash mismatch: $file"; exit 1; }
}

download_db finding_models
jq -e '.databases.anatomic_locations' "$MANIFEST" >/dev/null && download_db anatomic_locations
