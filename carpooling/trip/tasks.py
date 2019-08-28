from __future__ import absolute_import, unicode_literals
from background_task import background
from django.core.mail import send_mail

from celery import shared_task
from carpooling.settings.base import EMAIL_HOST_USER
from trip.models import Trip

from .utils import SpotifyAgent


@shared_task
def spotify_delete_playlist(playlist_id):
    spotify_agent = SpotifyAgent()
    spotify_agent.delete_playlist(playlist_id)


@background
def notify(trip_id: int):
    trip = Trip.objects.get(id=trip_id)
    receivers = [user.email for user in trip.passengers.all()]
    receivers.append(trip.car_provider.email)
    # todo: if trip have edit change it
    send_mail(
        "start estimation",
        "your trip start estimation started !",
        EMAIL_HOST_USER,
        receivers,
        fail_silently=False,
    )
