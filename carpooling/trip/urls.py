from django.contrib.auth.decorators import login_required
from django.urls import path

from trip.views import SearchTripsManger, get_available_trips_view, get_active_trips_view, get_chat_interface, \
    TripVoteHandler, get_trip_page
from trip.views import  TripCreationHandler, TripGroupsManager, TripRequestManager, \
    get_owned_trips_view, get_public_trips_view, get_categorized_trips_view, get_group_trips_view

app_name = "trip"

urlpatterns = [
    path("create/", TripCreationHandler.as_view(), name='trip_creation'),
    path("<int:trip_id>/", get_trip_page, name='trip'),
    path("<int:trip_id>/group/add/", TripGroupsManager.as_view(), name='add_to_groups'),
    path('<int:trip_id>/request/', login_required(TripRequestManager.as_view()), name='trip_request'),
    path('', get_owned_trips_view, name='owned_trips'),
    path('public/', get_public_trips_view, name='public_trips'),
    path('group/', get_categorized_trips_view, name='categorized_trips'),
    path('group/<int:group_id>/', get_group_trips_view, name='group_trip'),
    path("<int:trip_id>/vote/", TripVoteHandler.as_view(), name='trip_vote'),

    path('active/', get_active_trips_view, name='active_trips'),
    path('all/', get_available_trips_view, name='available_trips'),
    path('search/', SearchTripsManger.as_view(), name='search_trips'),
    path('chat/<int:trip_id>/', get_chat_interface, name='trip_chat'),
]
