from django.urls import path
from . import views
from .mail import InboxHandler

app_name = "account"
urlpatterns = [
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('password/', views.PasswordHandler.handle, name='password'),
    path('profile/', views.profile, name='user_profile'),
    path('mail/', InboxHandler.handle_inbox, name='user-inbox'),
]
