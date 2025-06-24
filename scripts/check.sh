#!/bin/bash
# Read-only quality checks (for CI)

set -e

echo "🔍 Running Finding Model Forge quality checks..."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync --all-extras --dev
fi

echo "🔍 Checking linting..."
uv run ruff check .

echo "🎨 Checking code formatting..."
uv run ruff format --check .

echo "🔎 Running type checking..."
uv run mypy .

echo "✅ All quality checks passed!"
