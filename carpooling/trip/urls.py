from django.urls import path
from . import views

app_name = "trip"
urlpatterns = [
    path("", views.trip_init, name='trip_init'),
    path("create/", views.trip_creation, name='trip_creation'),
]
