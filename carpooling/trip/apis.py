import json

from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from root.decorators import only_get_allowed
from .utils import ItemType

from trip.models import Trip
from .utils import SpotifyAgent


def spotify_search(request, trip_id, query):
    if request.method == "GET":
        search_result = search(query)
        append_add_to_playlist_url(search_result, trip_id)
        result = {'items': search_result}
        return HttpResponse(json.dumps(result))
    else:
        return HttpResponseBadRequest('Method not implemented')


def search(query):
    search_results = []
    spotify_agent = SpotifyAgent()
    search_results.extend(spotify_agent.search_items(query, ItemType.TRACK))
    search_results.extend(spotify_agent.search_items(query, ItemType.ALBUM))
    return search_results


@only_get_allowed
def add_to_playlist(request, trip_id, item_id, item_type):
    playlist_id = Trip.objects.get(id=trip_id).playlist_id
    SpotifyAgent().add_item_to_playlist(playlist_id, item_id, item_type)
    return redirect(reverse('trip:trip', kwargs={"trip_id": trip_id}))


def append_add_to_playlist_url(items, trip_id):
    for item in items:
        item['url'] = reverse('trip:add_to_playlist', kwargs={'trip_id': trip_id, 'item_id': item['id'],
                                                              'item_type': item['type']})
