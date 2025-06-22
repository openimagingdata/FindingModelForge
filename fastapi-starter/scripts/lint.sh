#!/bin/bash
# Code formatting and linting script

set -e

echo "🎨 Formatting and linting FastAPI Starter code..."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync --all-extras --dev
fi

echo "🔧 Fixing code formatting..."
uv run ruff format .

echo "🔍 Fixing linting issues..."
uv run ruff check --fix .

echo "🔎 Running type checking..."
uv run mypy .

echo "✅ Code formatting and linting complete!"