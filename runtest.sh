#!/bin/bash
while [ $(curl --silent --output /dev/null --write-out "%{http_code}" elasticsearch:9200) != 200 ]
do
	sleep 0.5
done
cd /code/carpooling
python3 manage.py test
