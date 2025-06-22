#!/bin/bash
# Production Docker build script

set -e

echo "🐳 Building FastAPI Starter Docker image..."

# Build the production image
docker build -t fastapi-starter:latest -t fastapi-starter:$(date +%Y%m%d) .

echo "📊 Image sizes:"
docker images fastapi-starter --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo "✅ Docker build complete!"

# Optional: Push to registry
# echo "📤 Pushing to registry..."
# docker push fastapi-starter:latest
# docker push fastapi-starter:$(date +%Y%m%d)