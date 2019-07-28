from django.urls import path
from . import views


app_name = "account"
urlpatterns = [
    path('login/', views.login_init, name='login'),
    path('signup/', views.signup, name='signup'),
]
