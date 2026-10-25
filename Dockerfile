# ==============================================================================
# Production Dockerfile for Mutual Fund FAQ RAG Backend (Railway.app)
# ==============================================================================
FROM python:3.11-slim as base

# Prevent Python from writing .pyc files and force unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer model into container cache to prevent runtime cold start delays
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application source code, corpus data, and operational scripts
COPY src/ /app/src/
COPY data/ /app/data/
COPY scripts/ /app/scripts/

# Ensure persistent data directories exist and entrypoint is executable with LF line endings
RUN mkdir -p /app/data/chromadb /app/data/sessions /app/data/raw /app/data/processed && \
    sed -i 's/\r$//' /app/scripts/entrypoint.sh && \
    chmod +x /app/scripts/entrypoint.sh

# Non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Expose dynamic Railway PORT
EXPOSE 8000

# Entrypoint sanitizes arguments (e.g. literal $PORT) and launches the backend
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "-m", "src.api.main"]
