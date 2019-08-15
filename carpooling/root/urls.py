from django.urls import path
from .views import HomeManager, SearchPeopleManager

app_name = "root"
urlpatterns = [
    path("", HomeManager.as_view(), name='home'),
    path("search/people/<query>", SearchPeopleManager.search_people_view, name='search_people'),
]
