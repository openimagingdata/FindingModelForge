#!/bin/bash
# Run tests with quality checks

set -e

echo "🧪 Running Finding Model Forge tests..."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync --all-extras --dev
fi

echo "🔍 Running linting..."
uv run ruff check .

echo "🎨 Checking code formatting..."
uv run ruff format --check .

echo "🔎 Running type checking..."
uv run mypy .

echo "📋 Running tests with coverage..."
uv run pytest --cov=app --cov-report=term-missing --cov-report=html

echo "✅ All tests and quality checks passed!"