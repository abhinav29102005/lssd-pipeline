# Backend Dockerfile for Railway
# Multi-service HPC scheduler with FastAPI, Raft consensus, and cluster simulator

FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing bytecode and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies for PostgreSQL and Redis
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY src /app/src

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Railway provides the PORT environment variable dynamically
# Default to 8000 for local testing
ENV PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "
import urllib.request
import sys
port = __import__('os').getenv('PORT', '8000')
try:
    urllib.request.urlopen(f'http://localhost:{port}/health', timeout=5)
    sys.exit(0)
except:
    sys.exit(1)
" || exit 1

# Expose the port (documentation purposes)
EXPOSE $PORT

# Run all backend services via the startup script
CMD ["/app/start.sh"]
