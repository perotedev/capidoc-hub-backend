#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding default admin (if configured and missing)..."
python -m app.seed

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
