# Stage 1: Build & Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Minimal Production Runtime
FROM python:3.11-slim

WORKDIR /app

# Non-root service user for fintech process security
RUN addgroup --system appgroup && adduser --system --group appuser

COPY --from=builder /install /usr/local
COPY backend /app/backend
COPY frontend /app/frontend
COPY data /app/data

ENV PYTHONPATH=/app/backend

USER appuser

EXPOSE 8000

# Container Healthcheck Probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]