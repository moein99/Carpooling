from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.contrib.gis.db import models as gis_models

# Create your models here.
from account.models import Member
from group.models import Group


class Trip(models.Model):
    STATUS_CHOICES = [
        ('wa', 'waiting'),
        ('cl', 'closed'),
        ('in', 'in route'),
        ('dn', 'done')
    ]
    source = gis_models.PointField()
    destination = gis_models.PointField()
    is_private = models.BooleanField(default=False)
    passengers = models.ManyToManyField(Member, through="Companionship", related_name='partaking_trips')
    requests = models.ManyToManyField(Member, through="TripRequest", related_name='requests')
    groups = models.ManyToManyField(Group, through="TripGroups")
    car_provider = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name='driving_trips', null=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    capacity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(20)])
    start_estimation = models.DateTimeField()
    end_estimation = models.DateTimeField()


class Companionship(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    source = gis_models.PointField()
    destination = gis_models.PointField()


class TripGroups(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)


class TripRequest(models.Model):
    applicant = models.ForeignKey(Member, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    source = gis_models.PointField()
    destination = gis_models.PointField()