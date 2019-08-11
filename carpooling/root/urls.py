from django.urls import path
from .views import HomeManager, SearchPeopleManager

app_name = "root"
urlpatterns = [
    path("", HomeManager.as_view(), name='home'),
    path("search/people/<query>", SearchPeopleManager.as_view(), name='search_people'),
]
