# DOI2BibTeX - Multi-stage Docker Build
# Phase 6.3a: Docker Setup
#
# This Dockerfile creates an optimized production image for DOI2BibTeX
# with support for Web UI, REST API, and CLI tools.
#
# Build: docker build -t doi2bibtex:latest .
# Run API: docker run -p 8000:8000 doi2bibtex:latest api
# Run Web: docker run -p 8501:8501 doi2bibtex:latest web
# Run CLI: docker run doi2bibtex:latest cli convert 10.1038/nature12373

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

LABEL maintainer="Ajay Khanna <akhanna2@ucmerced.edu>"
LABEL description="DOI2BibTeX - Enterprise-grade DOI to BibTeX converter"

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY core/ ./core/
COPY streamlit_app.py api_server.py cli.py ./
COPY tests/ ./tests/

# Build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# ============================================================================
# Stage 2: Runtime (API Server)
# ============================================================================
FROM python:3.11-slim as api

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash doi2bibtex && \
    mkdir -p /app/data /app/.cache && \
    chown -R doi2bibtex:doi2bibtex /app

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install application with all features
RUN pip install --no-cache-dir /tmp/*.whl[all] && \
    rm /tmp/*.whl

# Switch to non-root user
USER doi2bibtex

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command: Run API server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage 3: Runtime (Web UI)
# ============================================================================
FROM python:3.11-slim as web

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd -m -u 1000 -s /bin/bash doi2bibtex && \
    mkdir -p /app/data /app/.cache && \
    chown -R doi2bibtex:doi2bibtex /app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[all] && \
    rm /tmp/*.whl

USER doi2bibtex
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ============================================================================
# Stage 4: Runtime (CLI)
# ============================================================================
FROM python:3.11-slim as cli

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd -m -u 1000 -s /bin/bash doi2bibtex && \
    mkdir -p /app/data /app/.cache && \
    chown -R doi2bibtex:doi2bibtex /app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl[all] && \
    rm /tmp/*.whl

USER doi2bibtex

ENTRYPOINT ["doi2bibtex"]
CMD ["--help"]
