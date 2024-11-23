#!/usr/bin/env bash

# use path of this example as working directory; enables starting this script from anywhere
cd "$(dirname "$0")"

# Set PORT to FMF_API_PORT if it is set, otherwise default to 8000

if [ "$1" = "prod" ]; then
    PORT=${FMF_API_PORT:-80} 
    echo "Starting Uvicorn server in production mode..."
    # we also use a single worker in production mode so socket.io connections are always handled by the same worker
    uvicorn app.main:app --workers 1 --log-level warning --port $PORT
elif [ "$1" = "dev" ]; then
    PORT=${FMF_API_PORT:-8000} 
    echo "Starting Uvicorn server in development mode..."
    # reload implies workers = 1
    uvicorn app.main:app --reload --log-level info --port $PORT
else
    echo "Invalid parameter. Use 'prod' or 'dev'."
    exit 1
fi