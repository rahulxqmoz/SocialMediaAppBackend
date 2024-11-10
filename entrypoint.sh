#!/bin/sh

# Navigate to the directory where manage.py is located
cd /app  # Ensure this is the correct path to `manage.py`

python manage.py makemigrations
python manage.py migrate --no-input
python manage.py collectstatic --no-input

# Start Gunicorn server
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
