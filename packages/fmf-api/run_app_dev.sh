#!/usr/bin/env bash

# Fail unless we have the required environment variables
if [ -z "$GITHUB_CLIENT_ID" ] || [ -z "$GITHUB_CLIENT_SECRET" ]; then
    echo "Please set valid environment variables"
    exit 1
fi
# use path of this example as working directory; enables starting this script from anywhere
APP_DIR=/app
cd $APP_DIR

# Set PORT to FMF_API_PORT if it is set, otherwise default to 8000
PORT=${FMF_API_PORT:-8000}
echo "Starting Uvicorn server in dev mode..."
# we also use a single worker in production mode so socket.io connections are always handled by the same worker
exec uv run uvicorn app.main:app --reload --log-level info  --host localhost --port $PORT
