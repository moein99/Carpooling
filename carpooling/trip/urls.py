from django.urls import path
from trip.views import TripHandler, TripManageSystem

app_name = "trip"
urlpatterns = [
    path("create/", TripManageSystem.trip_creation, name='trip_creation'),
    path("<int:trip_id>/", TripManageSystem.trip_page, name='trip_page'),
    path("<int:trip_id>/group/add/", TripManageSystem.trip_add_groups, name='trip_add_groups'),

    path('', TripHandler.handle_owned_trips, name='owned-trips'),
    path('public/', TripHandler.handle_public_trips, name='public-trips'),
    path('group/', TripHandler.handle_categorized_trips, name='categorized-trips'),
    path('group/<int:group_id>/', TripHandler.handle_group_trips, name='group-trip'),
    path('active/', TripHandler.handle_active_trips, name='active-trips'),
    path('all/', TripHandler.handle_available_trips, name='available-trips')
]
