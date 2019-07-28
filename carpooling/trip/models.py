from django.core.validators import MaxValueValidator
from django.db import models

# Create your models here.
from account.models import Member


class Trip(models.Model):
    STATUS_CHOICES = [
        ('wa', 'waiting'),
        ('in', 'in route'),
        ('dn', 'done')
    ]
    destination_lat = models.DecimalField(max_digits=12, decimal_places=9)
    destination_lon = models.DecimalField(max_digits=12, decimal_places=9)
    source_lat = models.DecimalField(max_digits=12, decimal_places=9)
    source_lon = models.DecimalField(max_digits=12, decimal_places=9)
    is_private = models.BooleanField(default=False)
    passengers = models.ManyToManyField(Member, through="Companionship", related_name='partaking_trips')
    driver = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name='driving_trips', null=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    capacity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(20)])

    def get_source(self):
        return self.source_lat, self.source_lon

    def get_destination(self):
        return self.destination_lat, self.destination_lon


class Companionship(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)