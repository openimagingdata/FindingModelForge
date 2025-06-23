#!/bin/bash
# Production Docker build script

set -e

echo "🐳 Building Finding Model Forge Docker image..."

# Build the production image
docker build -t findingmodelforge:latest -t findingmodelforge:$(date +%Y%m%d) .

echo "📊 Image sizes:"
docker images findingmodelforge --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo "✅ Docker build complete!"

# Optional: Push to registry
# echo "📤 Pushing to registry..."
# docker push findingmodelforge:latest
# docker push findingmodelforge:$(date +%Y%m%d)