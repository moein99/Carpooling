from django.contrib import admin

# Register your models here.
from account.models import Member, Report

admin.site.register(Member)
admin.site.register(Report)

