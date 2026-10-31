#!/bin/sh
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Seeding demo data..."
python manage.py seed_demo

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
