from django.urls import path
from trip.views import TripHandler
app_name = "trip"
urlpatterns = [
    path('public/', TripHandler.handle_public_trip, name='public-trips'),
    path('group/', TripHandler.handle_group_trips, name='group-trips'),
    path('group/<int:id>/', TripHandler.handle_group_trips, name='trips-by-group'),
    #path('all/')
]

