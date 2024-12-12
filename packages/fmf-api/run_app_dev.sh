#!/usr/bin/env bash

# use path of this example as working directory; enables starting this script from anywhere
APP_DIR=/app
cd $APP_DIR

# Set PORT to FMF_API_PORT if it is set, otherwise default to 8000
PORT=${FMF_API_PORT:-8000}
echo "Starting Uvicorn server in dev mode..."
exec uv run uvicorn app.main:app --workers 1 --log-level info  --host 0.0.0.0 --port $PORT
