FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/data/chroma_db

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1

# This alternative CMD syntax sometimes works better with Railway
CMD gunicorn --bind "0.0.0.0:${PORT:-8000}" app:app