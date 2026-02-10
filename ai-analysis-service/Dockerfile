# ── builder stage ────────────────────────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && \
	apt-get install -y --no-install-recommends gcc libpq-dev && \
	rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt && \
	find /install -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; \
	find /install -type d -name 'tests' -exec rm -rf {} + 2>/dev/null; \
	find /install -type d -name 'test' -exec rm -rf {} + 2>/dev/null; \
	find /install -type f -name '*.pyc' -delete 2>/dev/null; \
	find /install -type f -name '*.pyo' -delete 2>/dev/null; \
	rm -rf /install/lib/python3.11/site-packages/numpy/tests \
	/install/lib/python3.11/site-packages/numpy/*/tests \
	/install/lib/python3.11/site-packages/sklearn/tests \
	/install/lib/python3.11/site-packages/sklearn/*/tests \
	/install/lib/python3.11/site-packages/sklearn/datasets/data \
	/install/lib/python3.11/site-packages/sklearn/datasets/descr \
	/install/lib/python3.11/site-packages/scipy/*/tests \
	/install/lib/python3.11/site-packages/scipy/linalg/tests \
	2>/dev/null; true

# ── runtime stage ────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && \
	apt-get install -y --no-install-recommends libpq5 curl && \
	rm -rf /var/lib/apt/lists/* && \
	groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser . .

RUN rm -rf tests/ htmlcov/ Makefile setup.cfg .flake8 .coverage __pycache__

USER appuser

ARG SERVICE_PORT=8005
ENV SERVICE_PORT=${SERVICE_PORT}
EXPOSE ${SERVICE_PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
	CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]
