#!/bin/bash
sleep 1
python3 /code/carpooling/manage.py migrate
python3 /code/carpooling/manage.py runserver 0.0.0.0:8000 & 
cd carpooling && celery -A carpooling worker -l info