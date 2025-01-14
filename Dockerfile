FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app/data/chroma_db /app/logs

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Expose port
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Logging configuration
ENV LOGGING_CONFIG=/app/logging.conf

# Use gunicorn with more diagnostic options
CMD ["gunicorn", \
     "--bind", "0.0.0.0:${PORT}", \
     "--log-level", "debug", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "app:app"]