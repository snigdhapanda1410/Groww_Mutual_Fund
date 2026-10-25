# ==============================================================================
# Production Dockerfile for Mutual Fund FAQ RAG Backend (Railway.app)
# ==============================================================================
FROM python:3.11-slim as base

# Prevent Python from writing .pyc files and force unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    WEB_CONCURRENCY=1 \
    HF_HOME=/app/data/cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/data/cache/sentence_transformers \
    NLTK_DATA=/app/data/cache/nltk_data \
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

# Pre-download SentenceTransformer model and NLTK tokenizers into container cache
RUN mkdir -p /app/data/cache/huggingface /app/data/cache/sentence_transformers /app/data/cache/nltk_data && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" && \
    python -c "import nltk; nltk.download('punkt', download_dir='/app/data/cache/nltk_data'); nltk.download('punkt_tab', download_dir='/app/data/cache/nltk_data')"

# Enforce offline mode at runtime so container never makes unauthenticated HF calls
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Copy application source code, corpus data, and operational scripts
COPY src/ /app/src/
COPY data/ /app/data/
COPY scripts/ /app/scripts/

# Ensure persistent directories exist, sanitize line endings, and replace uvicorn with wrapper
RUN mkdir -p /app/data/chromadb /app/data/sessions /app/data/raw /app/data/processed && \
    sed -i 's/\r$//' /app/scripts/entrypoint.sh && \
    sed -i 's/\r$//' /app/scripts/entrypoint.py && \
    sed -i 's/\r$//' /app/scripts/uvicorn_wrapper.py && \
    chmod +x /app/scripts/entrypoint.sh /app/scripts/entrypoint.py /app/scripts/uvicorn_wrapper.py && \
    cp /app/scripts/uvicorn_wrapper.py /usr/local/bin/uvicorn && \
    chmod +x /usr/local/bin/uvicorn

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
