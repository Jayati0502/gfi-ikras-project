FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Create data directory
RUN mkdir -p /app/data/chroma_db

# Environment variable for ChromaDB
ENV RAILWAY_VOLUME_MOUNT_PATH=/app/data/chroma_db

# Run the application
CMD gunicorn --bind 0.0.0.0:$PORT src.app:app
