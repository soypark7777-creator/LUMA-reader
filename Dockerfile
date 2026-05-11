# ══════════════════════════════════════════════
#  LUMA Dockerfile — 멀티스테이지 빌드
# ══════════════════════════════════════════════

# ── 빌드 스테이지 ──────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# ── 런타임 스테이지 ─────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY app/    ./app/
COPY app.py  .

ENV PATH=/root/.local/bin:$PATH \
    FLASK_ENV=production \
    FLASK_DEBUG=false \
    PORT=5000 \
    HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "-m", "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "app:app"]
