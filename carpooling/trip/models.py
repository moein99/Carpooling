from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q

from account.models import Member
from group.models import Group


class Trip(models.Model):
    WAITING_STATUS = 'wa'
    CLOSED_STATUS = 'cl'
    IN_ROUTE_STATUS = 'in'
    DONE_STATUS = 'dn'
    CANCELED_STATUS = 'ca'
    STATUS_CHOICES = [
        (WAITING_STATUS, 'waiting'),
        (CLOSED_STATUS, 'closed'),
        (IN_ROUTE_STATUS, 'in route'),
        (DONE_STATUS, 'done'),
        (CANCELED_STATUS, 'canceled')
    ]
    source = gis_models.PointField()
    destination = gis_models.PointField()
    is_private = models.BooleanField(default=False)
    passengers = models.ManyToManyField(Member, through="Companionship", related_name='partaking_trips')
    groups = models.ManyToManyField(Group, through="TripGroups")
    car_provider = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name='driving_trips', null=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    capacity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(20)])
    start_estimation = models.DateTimeField()
    end_estimation = models.DateTimeField()
    trip_description = models.CharField(max_length=200, null=True)
    playlist_id = models.CharField(max_length=22, null=True)

    @classmethod
    def get_accessible_trips_for(cls, user):
        return cls.objects.filter(Q(is_private=False) | Q(groups__membership__member=user) | Q(car_provider=user) | Q(
            companionship__member=user))


class Companionship(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    source = gis_models.PointField()
    destination = gis_models.PointField()


class TripGroups(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)


class TripRequestSet(models.Model):
    title = models.CharField(max_length=50, null=True)
    applicant = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='trip_request_sets')
    closed = models.BooleanField(default=False)

    def close(self):
        self.requests.exclude(status=TripRequest.ACCEPTED_STATUS).update(status=TripRequest.CANCELED_STATUS)
        self.closed = True
        self.save()

    def __str__(self):
        return str(self.id) + '' + self.title


class TripRequest(models.Model):
    PENDING_STATUS = 'p'
    ACCEPTED_STATUS = 'a'
    CANCELED_STATUS = 'c'
    DECLINED_STATUS = 'd'

    STATUS_CHOICES = [
        (PENDING_STATUS, 'pending'),
        (ACCEPTED_STATUS, 'accepted'),
        (CANCELED_STATUS, 'canceled'),
        (DECLINED_STATUS, 'declined')
    ]
    containing_set = models.ForeignKey(TripRequestSet, on_delete=models.CASCADE, related_name='requests')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='requests')
    source = gis_models.PointField()
    destination = gis_models.PointField()
    creation_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=PENDING_STATUS)


class Vote(models.Model):
    receiver = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="received_votes")
    sender = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name="sent_votes", null=True)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True)
    rate = models.FloatField()
