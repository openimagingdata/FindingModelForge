# Multi-stage Dockerfile for Finding Model Forge

# Frontend build stage
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install Node.js dependencies (including devDependencies for build)
RUN npm ci

# Copy source files needed for build
COPY src/ ./src/
COPY vite.config.js ./

# Build frontend assets
RUN npm run build

# Python build stage
FROM python:3.13-slim-bullseye AS python-builder

# Ensure all security updates are applied
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y build-essential curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache --no-dev

# Production stage
FROM python:3.13-slim-bullseye AS production

# Update package lists and install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install system dependencies for runtime
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /home/appuser/.cache/findingmodel \
    && chown -R appuser:appuser /home/appuser

# Set work directory
WORKDIR /app

# Copy uv from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment from python builder
COPY --from=python-builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy built frontend assets from frontend builder
COPY --from=frontend-builder --chown=appuser:appuser /app/static/ /app/static/

# Copy application code
COPY --chown=appuser:appuser . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"
ENV FORWARDED_ALLOW_IPS="*"

# Change to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
