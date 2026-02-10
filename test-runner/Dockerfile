FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runner.py .
COPY static/ static/

EXPOSE 8006

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')" || exit 1

CMD ["uvicorn", "runner:app", "--host", "0.0.0.0", "--port", "8006"]
