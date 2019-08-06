from django.contrib import admin

# Register your models here.
from account.models import Member

admin.site.register(Member)