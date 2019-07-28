from django.urls import path
from . import views


app_name = "account"
urlpatterns = [
    path('login/', views.login_handler, name='login'),
    path('signup/', views.signup_handler, name='signup'),
]
