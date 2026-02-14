FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  unzip \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Initialize Reflex (generate necessary files)
RUN reflex init

# Set environment variables
ENV API_URL=http://api:8000

# Expose ports
# 3002: Frontend
# 3003: Reflex backend (WebSocket)
EXPOSE 3002 3003

# Run Reflex application
CMD ["reflex", "run", "--loglevel", "warning", "--backend-port", "3003", "--frontend-port", "3002", "--backend-host", "0.0.0.0"]
