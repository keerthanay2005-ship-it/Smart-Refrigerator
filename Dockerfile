# ============================================================
# Smart Refrigerator — Production Docker Image
# Base : Python 3.11-slim (Debian bookworm)
# ============================================================

FROM python:3.11-slim

# ── Build-time labels ────────────────────────────────────────
LABEL maintainer="Smart Refrigerator" \
      version="1.0.0" \
      description="AI-powered Smart Refrigerator Management System"

# ── Runtime env defaults (override at compose / run time) ────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    DB_BACKEND=sqlite \
    SQLITE_DB_PATH=/app/data/smart_fridge.db \
    PORT=5000

# ── System dependencies ──────────────────────────────────────
# opencv-python-headless needs libglib2.0-0 only (no X11/GL).
# Pillow needs libjpeg / libpng.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libjpeg-dev \
        libpng-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user for security ────────────────────────
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --no-create-home appuser

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (separate layer — cached until reqs change) ──
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────
COPY . .

# ── Persistent data directory (SQLite DB lives here) ─────────
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# ── Drop privileges ───────────────────────────────────────────
USER appuser

# ── Volume for persistent SQLite data ────────────────────────
VOLUME ["/app/data"]

# ── Expose Flask port ─────────────────────────────────────────
EXPOSE 5000

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# ── Start with Gunicorn (production WSGI server) ─────────────
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
