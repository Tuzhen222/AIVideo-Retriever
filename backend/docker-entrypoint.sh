#!/bin/bash
set -e

echo "🚀 Starting backend container..."

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to be ready..."
QDRANT_HOST=${QDRANT_HOST:-qdrant}
QDRANT_HTTP_PORT=${QDRANT_HTTP_PORT:-6333}
QDRANT_WAIT_TIMEOUT=${QDRANT_WAIT_TIMEOUT:-20}
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $QDRANT_WAIT_TIMEOUT ]; do
  if curl -s -f --max-time 2 "http://${QDRANT_HOST}:${QDRANT_HTTP_PORT}/health" > /dev/null 2>&1; then
    echo "✅ Qdrant is ready!"
    break
  fi
  if [ $((WAIT_COUNT % 10)) -eq 0 ]; then
    echo "   Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_HTTP_PORT}... (${WAIT_COUNT}s/${QDRANT_WAIT_TIMEOUT}s)"
  fi
  sleep 2
  WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -ge $QDRANT_WAIT_TIMEOUT ]; then
  echo "⚠️  Qdrant not ready after ${QDRANT_WAIT_TIMEOUT}s, but continuing..."
fi

# Run ingest if bin files exist
# Use INDEX_DIR from env or default path
INDEX_DIR=${INDEX_DIR:-app/data/index}
BIN_DIR="/app/${INDEX_DIR}/bin"
echo "🔍 Checking for .bin files in ${BIN_DIR}..."
if [ -d "$BIN_DIR" ]; then
    BIN_COUNT=$(ls -1 $BIN_DIR/*.bin 2>/dev/null | wc -l)
    echo "   Found ${BIN_COUNT} .bin file(s)"
    if [ "$BIN_COUNT" -gt 0 ]; then
        echo "📦 Running ingest for ${BIN_COUNT} .bin file(s)..."
        if python -m app.services.vector_db.ingest; then
            echo "✅ Ingest completed successfully!"
        else
            echo "⚠️  Ingest completed with warnings (collections may already exist)"
        fi
    else
        echo "ℹ️  No .bin files found in ${BIN_DIR}"
    fi
else
    echo "⚠️  Directory ${BIN_DIR} does not exist"
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec "$@"

