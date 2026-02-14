FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
  && find /usr/local -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Copy application code
COPY simple_sns/ ./simple_sns/
COPY rxconfig.py .

# Initialize Reflex (generate necessary files)
RUN reflex init

# Set environment variables
ENV API_URL=http://api:8000 \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1

# Expose ports
# 3002: Frontend
# 3003: Reflex backend (WebSocket)
EXPOSE 3002 3003

# Run Reflex application
CMD ["reflex", "run", "--loglevel", "warning", "--backend-port", "3003", "--frontend-port", "3002", "--backend-host", "0.0.0.0"]
