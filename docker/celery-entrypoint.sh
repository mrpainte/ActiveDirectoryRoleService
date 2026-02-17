#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-postgres}" -p "${DB_PORT:-5432}" -U "${DB_USER:-ad_manager}" -q; do
    echo "PostgreSQL is not ready - sleeping 2s"
    sleep 2
done
echo "PostgreSQL is ready."

echo "Waiting for Redis..."
REDIS_URL="${CELERY_BROKER_URL:-redis://redis:6379/0}"
until python -c "
import sys
try:
    from urllib.parse import urlparse
    parsed = urlparse('${REDIS_URL}')
    import socket
    s = socket.create_connection((parsed.hostname, parsed.port or 6379), timeout=2)
    s.close()
except Exception:
    sys.exit(1)
"; do
    echo "Redis is not ready - sleeping 2s"
    sleep 2
done
echo "Redis is ready."

echo "Starting Celery worker..."
exec celery -A ad_manager worker -l info
