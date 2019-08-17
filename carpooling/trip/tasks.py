from background_task import background
from django.core.mail import send_mail

from carpooling.settings import EMAIL_HOST_USER
from trip.models import Trip


@background
def notify(trip_id: int):
    trip = Trip.objects.get(id=trip_id)
    # todo: if trip have edit change it
    send_mail(
        "start estimation",
        "your trip start estimation started !",
        EMAIL_HOST_USER,
        [user.email for user in trip.passengers].append(trip.car_provider.email),
        fail_silently=False,
    )
    return
