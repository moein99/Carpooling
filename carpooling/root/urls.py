from django.urls import path
from .views import home_init

app_name = "root"
urlpatterns = [
    path("", home_init, name='home')
]
