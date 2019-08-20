from django.contrib.auth.decorators import login_required
from django.urls import path

from trip.views import AutomaticJoinRequestManager, SearchTripsManager, get_available_trips_view, \
    get_active_trips_view, get_playlist_view, TripCreationManger, TripGroupsManager, TripRequestManager, \
    get_owned_trips_view, get_public_trips_view, get_categorized_trips_view, get_group_trips_view, get_chat_interface, \
    get_trip_page_view, TripVoteManager
from .apis import spotify_search, add_to_playlist

app_name = "trip"

urlpatterns = [
    path("create/", login_required(TripCreationManger.as_view()), name='trip_creation'),
    path("<int:trip_id>/", get_trip_page_view, name='trip'),
    path("<int:trip_id>/group/add/", TripGroupsManager.as_view(), name='add_to_groups'),
    path('<int:trip_id>/request/', login_required(TripRequestManager.as_view()), name='trip_request'),
    path('', get_owned_trips_view, name='owned_trips'),
    path('public/', get_public_trips_view, name='public_trips'),
    path('group/', get_categorized_trips_view, name='categorized_trips'),
    path('group/<int:group_id>/', get_group_trips_view, name='group_trip'),
    path("<int:trip_id>/vote/", TripVoteManager.as_view(), name='trip_vote'),

    path('active/', get_active_trips_view, name='active_trips'),
    path('all/', get_available_trips_view, name='available_trips'),
    path('search/', login_required(SearchTripsManager.as_view()), name='search_trips'),

    path('automatic-join/', login_required(AutomaticJoinRequestManager.as_view()), name='automatically_join_trip'),
    path('<int:trip_id>/playlist', get_playlist_view, name='trip_music_player'),
    path('spotify-search/<int:trip_id>/<query>', spotify_search, name='spotify_search'),
    path('<int:trip_id>/playlist/<str:item_id>/<str:item_type>', add_to_playlist,
         name='add_to_playlist'),
    path('chat/<int:trip_id>/', get_chat_interface, name='trip_chat'),
]
