from django.contrib.auth.decorators import login_required
from django.urls import path

from trip.views import SearchTripsManager, get_available_trips_view, get_active_trips_view, AutomaticJoinRequestManager
from trip.views import TripHandler, TripCreationManger, TripGroupsManager, TripRequestManager, \
    get_owned_trips_view, get_public_trips_view, get_categorized_trips_view, get_group_trips_view

app_name = "trip"

urlpatterns = [
    path("create/", TripCreationManger.as_view(), name='trip_creation'),
    path("<int:trip_id>/", TripHandler.as_view(), name='trip'),
    path("<int:trip_id>/group/add/", TripGroupsManager.as_view(), name='add_to_groups'),
    path('<int:trip_id>/request/', login_required(TripRequestManager.as_view()), name='trip_request'),
    path('', get_owned_trips_view, name='owned_trips'),
    path('public/', get_public_trips_view, name='public_trips'),
    path('group/', get_categorized_trips_view, name='categorized_trips'),
    path('group/<int:group_id>/', get_group_trips_view, name='group_trip'),

    path('active/', get_active_trips_view, name='active_trips'),
    path('all/', get_available_trips_view, name='available_trips'),
    path('search/', SearchTripsManager.as_view(), name='search_trips'),

    path('automatic-join/', AutomaticJoinRequestManager.as_view(), name='automatically_join_trip')
]
