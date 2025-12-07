FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (docker CLI and curl for healthcheck)
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app and OAuth modules
COPY backend/app.py .
COPY backend/oauth.py .
COPY backend/models.py .

# Copy Alembic configuration
COPY backend/alembic.ini .
COPY backend/alembic ./alembic

# Copy source code from parent directory
COPY src /app/src

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 5001

# Disable Python output buffering for real-time logs
ENV PYTHONUNBUFFERED=1

# Run the application with Gunicorn
# --timeout 300: 5 minutes timeout for LLM processing
# --workers 1: Single worker to avoid concurrency issues (see TODO in app.py)
# --bind 0.0.0.0:5001: Listen on all interfaces
# --access-logfile -: Log HTTP requests to stdout
# --error-logfile -: Log errors to stderr
# --log-level info: Show info level logs
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "300", "--workers", "1", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "app:app"]
