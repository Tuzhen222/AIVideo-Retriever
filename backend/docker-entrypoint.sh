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

# Wait for Elasticsearch to be ready (if configured)
if [ -n "${ELASTICSEARCH_HOST}" ]; then
  echo "⏳ Waiting for Elasticsearch to be ready..."
  ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST:-elasticsearch}
  ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}
  ELASTICSEARCH_WAIT_TIMEOUT=${ELASTICSEARCH_WAIT_TIMEOUT:-30}
  ES_WAIT_COUNT=0

  while [ $ES_WAIT_COUNT -lt $ELASTICSEARCH_WAIT_TIMEOUT ]; do
    if curl -s -f --max-time 2 "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}/_cluster/health" > /dev/null 2>&1; then
      echo "✅ Elasticsearch is ready!"
      break
    fi
    if [ $((ES_WAIT_COUNT % 10)) -eq 0 ]; then
      echo "   Waiting for Elasticsearch at ${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}... (${ES_WAIT_COUNT}s/${ELASTICSEARCH_WAIT_TIMEOUT}s)"
    fi
    sleep 2
    ES_WAIT_COUNT=$((ES_WAIT_COUNT + 2))
  done

  if [ $ES_WAIT_COUNT -ge $ELASTICSEARCH_WAIT_TIMEOUT ]; then
    echo "⚠️  Elasticsearch not ready after ${ELASTICSEARCH_WAIT_TIMEOUT}s, but continuing..."
  fi
fi

# Run Qdrant ingest if bin files exist
# Use INDEX_DIR from env or default path
INDEX_DIR=${INDEX_DIR:-app/data/index}
BIN_DIR="/app/${INDEX_DIR}/bin"
echo "🔍 Checking for .bin files in ${BIN_DIR}..."
if [ -d "$BIN_DIR" ]; then
    BIN_COUNT=$(ls -1 $BIN_DIR/*.bin 2>/dev/null | wc -l)
    echo "   Found ${BIN_COUNT} .bin file(s)"
    if [ "$BIN_COUNT" -gt 0 ]; then
        echo "📦 Running Qdrant ingest for ${BIN_COUNT} .bin file(s)..."
        if python -m app.services.vector_db.ingest; then
            echo "✅ Qdrant ingest completed successfully!"
        else
            echo "⚠️  Qdrant ingest completed with warnings (collections may already exist)"
        fi
    else
        echo "ℹ️  No .bin files found in ${BIN_DIR}"
    fi
else
    echo "⚠️  Directory ${BIN_DIR} does not exist"
fi

# Run Elasticsearch ingest if JSON files exist in es_data
ES_DATA_DIR="/app/${INDEX_DIR}/es_data"
echo "🔍 Checking for JSON files in ${ES_DATA_DIR}..."
if [ -d "$ES_DATA_DIR" ]; then
    JSON_COUNT=$(ls -1 $ES_DATA_DIR/*.json 2>/dev/null | wc -l)
    echo "   Found ${JSON_COUNT} JSON file(s)"
    if [ "$JSON_COUNT" -gt 0 ]; then
        echo "📦 Running Elasticsearch ingest for ${JSON_COUNT} JSON file(s)..."
        if python -m app.services.elastic_search.ingest; then
            echo "✅ Elasticsearch ingest completed successfully!"
        else
            echo "⚠️  Elasticsearch ingest completed with warnings (indices may already exist)"
        fi
    else
        echo "ℹ️  No JSON files found in ${ES_DATA_DIR}"
    fi
else
    echo "ℹ️  Directory ${ES_DATA_DIR} does not exist (Elasticsearch ingest skipped)"
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec "$@"

