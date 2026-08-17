# === backend/Dockerfile ===
# Multi-stage, non-root production Dockerfile with dev-mode target

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11.9-slim AS builder

WORKDIR /app

# Set up virtual environment & install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Production (Runtime) ────────────────────────────────────────────
FROM python:3.11.9-slim AS production

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user and prepare writable app directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Copy application code with non-root ownership
COPY --chown=appuser:appuser . /app

USER appuser

EXPOSE 8000

# Health check using standard library urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production default command (no --reload). Alembic owns the schema, so the
# container brings the database up to head before serving (see MIGRATIONS.md).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# ── Stage 3: Development (Hot-reload mode) ───────────────────────────────────
FROM production AS development

USER appuser

# Development command with hot reload enabled
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
