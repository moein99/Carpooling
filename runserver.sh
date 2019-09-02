#!/bin/bash
while [ $(curl --silent --output /dev/null --write-out "%{http_code}" elasticsearch:9200) != 200 ]
do
	sleep 0.5
done
python3 /code/carpooling/manage.py migrate
python3 /code/carpooling/manage.py runserver 0.0.0.0:8000 &
python3 /code/carpooling/manage.py process_tasks &
cd carpooling && celery -A carpooling worker -l info
