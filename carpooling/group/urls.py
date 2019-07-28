from django.urls import path

from group.views import create_group

app_name = "group"
urlpatterns = [
    path('', create_group, name="groups"),
]
