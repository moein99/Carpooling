from django.contrib import admin

# Register your models here.
from trip.models import Trip, TripGroups, TripRequest, Companionship

admin.site.register(Trip)
admin.site.register(TripGroups)
admin.site.register(TripRequest)
admin.site.register(Companionship)
