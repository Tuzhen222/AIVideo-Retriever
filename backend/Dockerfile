FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./


RUN uv pip install --system --no-cache \
    fastapi==0.104.1 \
    "uvicorn[standard]==0.24.0" \
    pydantic-settings==2.1.0 \
    python-multipart==0.0.6 \
    qdrant-client==1.7.0 \
    "numpy>=1.26.0" \
    tqdm==4.66.1 \
    "faiss-cpu>=1.7.4" \
    "requests>=2.31.0" \
    "Pillow>=10.0.0" \
    "elasticsearch>=8.0.0,<9.0.0" \
    "cohere>=5.0.0" \
    "deep-translator>=1.11.4" \
    "google-generativeai>=0.3.0" \
    "psycopg2-binary>=2.9.9" 

# Copy application code (excluding data due to .dockerignore)
COPY app/ ./app/

# Copy .env file if exists (optional, will be overridden by docker-compose env_file)
COPY .env* ./

# Copy entrypoint script and fix line endings (CRLF to LF for Windows)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command with multiple workers for better concurrency
# Workers = 2 * CPU cores + 1 is recommended, using 4 workers for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

