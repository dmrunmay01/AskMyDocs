# ─────────────────────────────────────────────
# AskMyDocs API Dockerfile
# ─────────────────────────────────────────────

FROM python:3.11-slim AS base

# Prevent Python from creating .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────

FROM base AS dependencies

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ─────────────────────────────────────────────
# Runtime
# ─────────────────────────────────────────────

FROM dependencies AS runtime

WORKDIR /app

# Copy application code
COPY app ./app

# Create storage directories
RUN mkdir -p /app/storage/uploads \
    /app/storage/vectorstore

EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]