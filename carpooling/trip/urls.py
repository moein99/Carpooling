from django.urls import path
from trip.views import TripHandler, TripCreationHandler, TripGroupsManager, OwnedTripsManager, PublicTripsManager, \
    CategorizedTripsManager, GroupTripsManager, ActiveTripsManager, AvailableTripsManager
from trip.views import SearchTripsManger

app_name = "trip"

urlpatterns = [
    path("create/", TripCreationHandler.as_view(), name='trip_creation'),
    path("<int:trip_id>/", TripHandler.as_view(), name='trip'),
    path("<int:trip_id>/group/add/", TripGroupsManager.as_view(), name='add_to_groups'),
    path('', OwnedTripsManager.as_view(), name='owned_trips'),
    path('public/', PublicTripsManager.as_view(), name='public_trips'),
    path('group/', CategorizedTripsManager.as_view(), name='categorized_trips'),
    path('group/<int:group_id>/', GroupTripsManager.as_view(), name='group_trip'),

    path('active/', ActiveTripsManager.as_view(), name='active_trips'),
    path('all/', AvailableTripsManager.as_view(), name='available_trips'),
    path('search/', SearchTripsManger.as_view(), name='search_trips'),
]

