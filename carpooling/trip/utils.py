import os

import numpy as np
import requests
import spotipy
from django.contrib.gis.geos import Point
from django.utils import timezone
from numpy.linalg import norm

from carpooling.settings import SPOTIFY_CLIENT_ID, SPOTIFY_USERNAME, SPOTIFY_CLIENT_SECRET, \
    SPOTIFY_REFRESH_TOKEN

proxy = 'proxy.roo.cloud:3128'


class ItemType:
    TRACK = "track"
    ALBUM = "album"
    ALBUMS = "albums"
    ARTIST = "artist"
    ARTISTS = "artists"
    PLAYLIST = "playlist"
    TRACKS = "tracks"
    ITEMS = "items"


class SpotifyAgent:
    def __init__(self):
        self.access_token = None
        self.token_start_time = None
        self.expiration_time = None
        self.refresh_token = SPOTIFY_REFRESH_TOKEN
        self.TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"
        SpotifyAgent.set_proxy()
        self.refresh_access_token()
        self.spotify = spotipy.Spotify(auth=self.access_token)

    @staticmethod
    def set_proxy():
        os.environ['http_proxy'] = proxy
        os.environ['HTTP_PROXY'] = proxy
        os.environ['https_proxy'] = proxy
        os.environ['HTTPS_PROXY'] = proxy

    def refresh_access_token(self):
        data, headers = self.get_auth_data_and_headers()
        response = requests.post(url=self.TOKEN_ENDPOINT, data=data, headers=headers).json()
        if 'access_token' in response:
            self.set_new_access_token(response)
        else:
            raise ConnectionError("Couldn't refresh access token")

    def set_new_access_token(self, response):
        self.access_token = response['access_token']
        self.token_start_time = timezone.now()
        self.expiration_time = int(response['expires_in'])
        if 'refresh_token' in response:
            self.refresh_token = response['refresh_token']

    def get_auth_data_and_headers(self):
        data = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token,
                'client_id': SPOTIFY_CLIENT_ID, 'client_secret': SPOTIFY_CLIENT_SECRET}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return data, headers

    def create_playlist(self, playlist_name):
        if not self.is_access_token_active():
            self.refresh_access_token()
        response = self.spotify.user_playlist_create(SPOTIFY_USERNAME, playlist_name, public=True)
        return response['id']

    def is_access_token_active(self):
        cur_time = timezone.now()
        if (cur_time - self.token_start_time).total_seconds() < self.expiration_time - 100:
            return True
        return False

    def search_items(self, query, item_type):
        result = []
        response = self.spotify.search(q=item_type + ':' + query, type=item_type, limit=5)
        for item in response[item_type + 's'][ItemType.ITEMS]:
            result.append(SpotifyAgent.get_item_json(item, item_type))
        return result

    @staticmethod
    def get_item_json(item, item_type):
        artists = ' '.join(SpotifyAgent.get_artists_name(item[ItemType.ARTISTS]))
        description = "[#] ".replace('#', item_type) + artists
        return {"id": item['id'], "title": item['name'], 'type': item_type,
                "description": description}

    @staticmethod
    def get_artists_name(artists_list):
        return [artist['name'] for artist in artists_list]

    def add_item_to_playlist(self, playlist_id, item_id, item_type):
        new_tracks_ids = []
        if item_type == ItemType.TRACK:
            new_tracks_ids.append(item_id)
        elif item_type == ItemType.ALBUM:
            new_tracks_ids.extend(self.get_album_tracks_ids(item_id))
        new_tracks_ids = self.filter_already_added_tracks(new_tracks_ids, playlist_id)
        if len(new_tracks_ids) != 0:
            self.spotify.user_playlist_add_tracks(SPOTIFY_USERNAME, playlist_id, new_tracks_ids)

    def get_album_tracks_ids(self, album_id):
        tracks = self.spotify.album_tracks(album_id)[ItemType.ITEMS]
        return [track['id'] for track in tracks]

    def filter_already_added_tracks(self, new_tracks_ids, playlist_id):
        playlist_tracks = self.spotify.user_playlist(SPOTIFY_USERNAME, playlist_id=playlist_id,
                                                     fields=[ItemType.TRACKS])
        already_added_tracks_ids = [track[ItemType.TRACK]['id'] for track in
                                    playlist_tracks[ItemType.TRACKS][ItemType.ITEMS]]
        return [track_id for track_id in new_tracks_ids if track_id not in already_added_tracks_ids]

    def delete_playlist(self, playlist_id):
        self.spotify.user_playlist_unfollow(SPOTIFY_USERNAME, playlist_id)


def extract_source(post_data):
    return Point(float(post_data['source_lat']), float(post_data['source_lng']))


def extract_destination(post_data):
    return Point(float(post_data['destination_lat']), float(post_data['destination_lng']))


def subtract_two_point(point1: Point, point2: Point):
    return Point(point1.x - point2.x, point1.y - point2.y)


def get_trip_score(trip, source: Point, destination: Point):
    source_to_trip_source = subtract_two_point(trip.source, source)
    destination_to_trip_destination = subtract_two_point(trip.destination, destination)
    trip_source_to_destination = subtract_two_point(trip.destination, trip.source)
    if np.dot(trip_source_to_destination, subtract_two_point(destination, source)) < 0:
        return np.inf
    else:
        if np.dot(source_to_trip_source, trip_source_to_destination) > 0:
            # distance to source dot
            to_source_distance = norm(source_to_trip_source)
        else:
            # distance to line
            to_source_distance = norm(np.cross(source_to_trip_source, trip_source_to_destination)) / norm(
                trip_source_to_destination)

        if np.dot(destination_to_trip_destination, trip_source_to_destination) < 0:
            # distance to source dot
            to_destination_distance = norm(destination_to_trip_destination)
        else:
            # distance to line
            to_destination_distance = norm(
                np.cross(destination_to_trip_destination, trip_source_to_destination)) / norm(
                trip_source_to_destination)

    return to_source_distance + to_destination_distance
