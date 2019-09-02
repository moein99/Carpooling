from .base import *

DEBUG = True
ELASTIC_SEARCH = Elasticsearch([{'host': 'localhost', 'port': 9200}])

ALLOWED_HOSTS = ['localhost']

