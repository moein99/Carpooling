#!/bin/bash
sleep 1
python3 /code/carpooling/manage.py migrate --settings carpooling.settings.production
python3 /code/carpooling/manage.py runserver 0.0.0.0:8000 --settings carpooling.settings.production
