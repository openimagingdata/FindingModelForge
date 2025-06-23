#!/bin/bash

# use path of this example as working directory; enables starting this script from anywhere
APP_DIR=/app
cd $APP_DIR

# set default values for environment variables if not already set
PORT=${PORT:-8000}
LOG_LEVEL=${LOG_LEVEL:-info}
WORKERS=${WORKERS:-1}
echo "Starting Uvicorn server on ${PORT}... ($WORKERS workers, ${LOG_LEVEL} log level)"
# we also use a single worker in production mode so socket.io connections are always handled by the same worker
exec uv run uvicorn findingmodelforge.main:app --workers $WORKERS --log-level $LOG_LEVEL --host 0.0.0.0 --port $PORT
