FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/data/chroma_db

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . /app/

# Remove the explicit PORT environment variable since Railway will provide it
# ENV PORT=8000 <- Remove this line

# Keep this for Python logging
ENV PYTHONUNBUFFERED=1

# Modified CMD to handle PORT more reliably
CMD gunicorn --bind "0.0.0.0:${PORT:-8000}" app:app