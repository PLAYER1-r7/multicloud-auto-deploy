FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  nodejs \
  npm \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports (frontend + backend)
EXPOSE 3000 8001

# Run Reflex
CMD ["reflex", "run", "--env", "prod", "--loglevel", "info"]
