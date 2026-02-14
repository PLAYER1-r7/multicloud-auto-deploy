#!/bin/bash
set -e

# Use PORT environment variable if set (for Cloud Run), otherwise use 3002
FRONTEND_PORT=${PORT:-3002}
# Backend port fixed to 3003 for WebSocket (unless single-port mode)
BACKEND_PORT=3003

# Check if we should use single-port mode (for Cloud Run)
if [ -n "$PORT" ]; then
  echo "Starting Reflex in production mode on single port $FRONTEND_PORT"
  exec reflex run \
    --env prod \
    --loglevel warning \
    --single-port \
    --backend-port "$FRONTEND_PORT" \
    --backend-host 0.0.0.0
else
  echo "Starting Reflex in production mode on port $FRONTEND_PORT (backend on $BACKEND_PORT)"
  exec reflex run \
    --env prod \
    --loglevel warning \
    --frontend-port "$FRONTEND_PORT" \
    --backend-port "$BACKEND_PORT" \
    --backend-host 0.0.0.0
fi
