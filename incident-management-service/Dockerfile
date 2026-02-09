# ── Stage 1: Build ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time system deps
RUN apt-get update && \
	apt-get install -y --no-install-recommends gcc libpq-dev && \
	rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────────
FROM python:3.11-slim

# Install only runtime deps, then upgrade all packages to patch CVEs
RUN apt-get update && \
	apt-get upgrade -y && \
	apt-get install -y --no-install-recommends libpq5 curl && \
	apt-get autoremove -y && \
	rm -rf /var/lib/apt/lists/*

# Remove setuid/setgid binaries to satisfy Trivy
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

# Create non-root user
RUN useradd -m -u 1001 -s /usr/sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=appuser:appuser . .

# Remove files not needed at runtime
RUN rm -rf tests/ htmlcov/ Makefile setup.cfg .flake8 .coverage __pycache__

# Switch to non-root user
USER appuser

ARG SERVICE_PORT=8002
ENV SERVICE_PORT=${SERVICE_PORT}
EXPOSE ${SERVICE_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
	CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]
