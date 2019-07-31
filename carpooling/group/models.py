from django.db import models
from django.contrib.gis.db import models as gis_models

from account.models import Member


class Group(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=50)
    is_private = models.BooleanField(default=False)
    description = models.TextField(null=True)
    members = models.ManyToManyField(Member, through='Membership')
    source = gis_models.PointField(null=True)


class Membership(models.Model):
    ROLES = [
        ('ow', 'owner'),
        ('me', 'member'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=2, choices=ROLES)

    class Meta:
        unique_together = ['member', 'group']
