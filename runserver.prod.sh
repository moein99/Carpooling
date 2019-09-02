#!/bin/bash
while [ $(curl --silent --output /dev/null --write-out "%{http_code}" elasticsearch:9200) != 200 ]
do
	sleep 0.5
done
cd carpooling
python3 manage.py migrate
gunicorn carpooling.wsgi:application --bind 0.0.0.0:8000 &
celery -A carpooling worker -l info & 
python3 manage.py process_tasks

