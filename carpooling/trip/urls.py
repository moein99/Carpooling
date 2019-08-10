from django.urls import path
from trip.views import TripHandler, TripCreationHandler, TripGroupsManager, OwnedTripsManager, PublicTripsManager, \
    CategorizedTripsManager, GroupTripsManager

app_name = "trip"

urlpatterns = [
    path("create/", TripCreationHandler.as_view(), name='trip_creation'),
    # path("<int:trip_id>/", TripHandler.as_view(), name='trip'),
    path("<int:trip_id>/group/add/", TripGroupsManager.as_view(), name='add_to_groups'),
    path('', OwnedTripsManager.as_view(), name='owned_trips'),
    path('public/', PublicTripsManager.as_view(), name='public_trips'),
    path('group/', CategorizedTripsManager.as_view(), name='categorized-trips'),


    path('group/<int:group_id>/', GroupTripsManager.as_view(), name='group-trip'),
    path('active/', TripHandler.handle_active_trips, name='active-trips'),
    path('all/', TripHandler.handle_available_trips, name='available-trips')
]

