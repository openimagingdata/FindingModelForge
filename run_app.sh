#!/usr/bin/env bash

# use path of this example as working directory; enables starting this script from anywhere
APP_DIR=/app
cd $APP_DIR

# Use PORT for PORT if it's set, otherwise default to 8000
PORT=${PORT:-8000}
echo "Starting Uvicorn server on ${PORT}..."
# we also use a single worker in production mode so socket.io connections are always handled by the same worker
exec uv run uvicorn findingmodelforge.main:app --workers 1 --log-level info  --host 0.0.0.0 --port $PORT
