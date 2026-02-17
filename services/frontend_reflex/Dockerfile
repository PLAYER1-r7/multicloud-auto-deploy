FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  unzip \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
  && find /usr/local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Copy application code
COPY simple_sns/ ./simple_sns/
COPY rxconfig.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Initialize and export Reflex (build for production)
RUN reflex init && reflex export

# Set environment variables
ENV API_URL=http://api:8000 \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

# Expose ports
# 3002: Frontend (in prod mode, built static files)
# 3003: Backend (WebSocket and API)
EXPOSE 3002 3003

# Run Reflex application
CMD ["./entrypoint.sh"]
