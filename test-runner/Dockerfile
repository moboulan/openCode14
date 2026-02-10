# ── builder stage ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── runtime stage ────────────────────────────────────────────
FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser runner.py .
COPY --chown=appuser:appuser static/ static/

USER appuser

EXPOSE 8006

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')" || exit 1

CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "8006"]
