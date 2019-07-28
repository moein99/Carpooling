from django.db import models

# Create your models here.
from account.models import Member


class Group(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=50)
    is_private = models.BooleanField(default=False)
    description = models.TextField(null=True)
    members = models.ManyToManyField(Member, through='Membership')
    source_lat = models.DecimalField(max_digits=12, decimal_places=9, null=True)
    source_lon = models.DecimalField(max_digits=12, decimal_places=9, null=True)

    def get_source(self):
        return self.source_lat, self.source_lon


class Membership(models.Model):
    ROLES = [
        ('ow', 'owner'),
        ('me', 'member'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=2, choices=ROLES)
