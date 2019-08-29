from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgres',
        'PORT': 5432,
        'HOST': 'db',
        'USER': 'carpooling',
    }
}
MONGO_HOST = 'mongo'

LOGGING['handlers']['mongolog']['connection'] = 'mongodb://mongo:27017'
