from django.urls import path
from trip.views import SearchTripsManger

app_name = "trip"
urlpatterns = [
    path('search/', SearchTripsManger.as_view(), name='search_trips'),
]
