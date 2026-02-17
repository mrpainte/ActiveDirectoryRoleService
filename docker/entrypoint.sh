#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-postgres}" -p "${DB_PORT:-5432}" -U "${DB_USER:-ad_manager}" -q; do
    echo "PostgreSQL is not ready - sleeping 2s"
    sleep 2
done
echo "PostgreSQL is ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    echo "Creating superuser (if not exists)..."
    python manage.py createsuperuser --noinput || true
fi

echo "Starting gunicorn..."
exec gunicorn --workers 4 --bind 0.0.0.0:8000 ad_manager.wsgi:application
