#!/usr/bin/env bash

# Fail unless we have the required environment variables
if [ -z "$INFISICAL_PROJECT_ID" ] || [ -z "$INFISICAL_CLIENT_ID" ] || [ -z "$INFISICAL_CLIENT_SECRET" ]; then
    echo "Please set the environment variables INFISICAL_PROJECT_ID, INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET."
    exit 1
fi
INFISICAL_TOKEN=$(infisical login --method=universal-auth --client-id=$INFISICAL_CLIENT_ID \
    --client-secret=$INFISICAL_CLIENT_SECRET --plain --silent)
# Echo a message that we have the Infisical token and the first 8 characters of it
echo "Infisical token: ${INFISICAL_TOKEN:0:8}..."

# use path of this example as working directory; enables starting this script from anywhere
APP_DIR=/app
cd $APP_DIR

# Use PORT if it is set, otherwise default to 8000
PORT=${PORT:-8000}
INFISICAL_ENV=${INFISICAL_ENV:-prod}
echo "Starting Uvicorn server with Infisical secrets from ${INFISICAL_ENV} on port ${PORT}..."
# we also use a single worker in production mode so socket.io connections are always handled by the same worker
exec infisical run --token $INFISICAL_TOKEN --projectId $INFISICAL_PROJECT_ID --env $INFISICAL_ENV -- uv run uvicorn app.main:app --workers 1 --log-level warning  --host 0.0.0.0 --port $PORT
