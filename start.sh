#!/usr/bin/env bash
# Exit on error
set -o errexit

# Run database migrations
alembic upgrade head

# Start the FastAPI app
exec uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8000}