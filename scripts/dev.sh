#!/bin/bash
# Development server startup script

set -e

echo "🚀 Starting Finding Model Forge development server..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your GitHub OAuth credentials"
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync --all-extras --dev
fi

# Run the development server
echo "🌐 Starting server on http://localhost:8000"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
