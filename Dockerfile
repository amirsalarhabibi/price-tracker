ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as a normal user; /data is where the SQLite file lives.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data

COPY app app
USER appuser
ENV DB_PATH=/data/prices.db

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
