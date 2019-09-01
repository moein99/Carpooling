#!/bin/bash
sleep 1
cd carpooling
python3 manage.py migrate
gunicorn carpooling.wsgi:application --bind 0.0.0.0:8000 && celery -A carpooling worker -l info
