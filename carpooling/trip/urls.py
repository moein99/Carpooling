from django.urls import path
from .views import TripManageSystem

app_name = "trip"
urlpatterns = [
    path("", TripManageSystem.trip_init, name='trip_init'),
    path("create/", TripManageSystem.trip_creation, name='trip_creation'),
    path("<int:trip_id>/", TripManageSystem.trip_page, name='trip_page'),
    path("<int:trip_id>/group/add/", TripManageSystem.trip_add_groups, name='trip_add_groups'),
]
