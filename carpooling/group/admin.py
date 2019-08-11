from django.contrib import admin

# Register your models here.
from group.models import Group, Membership

admin.site.register(Group)
admin.site.register(Membership)