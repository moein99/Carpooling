from django.urls import path
from account.views.utils import report
from account.views.password import PasswordHandler
from account.views.authentication import AuthenticationHandler
from account.views.userinterface import UserInterfaceHandler

app_name = "account"
urlpatterns = [
    path('login/', AuthenticationHandler.handle_login, name='login'),
    path('signup/', AuthenticationHandler.handle_signup, name='signup'),
    path('logout/', AuthenticationHandler.handle_logout, name='logout'),
    path('profile/<int:user_id>/', UserInterfaceHandler.handle_profile, name='user_profile'),
    path('profile/<int:user_id>/report/', report, name='report_member'),
    path('profile/edit/', UserInterfaceHandler.handle_edit_profile, name='edit'),
    path('password/reset/', PasswordHandler.handle, name='password'),
    path('password/change/', PasswordHandler.handle_change_password, name='change_password'),
]
