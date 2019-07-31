from django.urls import path
from trip.views import TripHandler
app_name = "trip"
urlpatterns = [
    path('', TripHandler.handle_owned_trips, name='owned-trips'),
    path('public/', TripHandler.handle_public_trips, name='public-trips'),
    path('group/', TripHandler.handle_categorized_trips, name='categorized-trips'),
    path('group/<int:group_id>/', TripHandler.handle_group_trips, name='group-trip'),
    path('active/', TripHandler.handle_active_trips, name='active-trips'),
    path('all/', TripHandler.handle_available_trips, name='available-trips')
]

