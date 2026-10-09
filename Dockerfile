ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
ENV DB_PATH=/data/prices.db
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
