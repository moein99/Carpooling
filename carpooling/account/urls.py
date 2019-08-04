from django.urls import path
from account.views import AuthorisationHandler, UserInterfaceHandler, report, PasswordHandler

app_name = "account"
urlpatterns = [
    path('login/', AuthorisationHandler.handle_login, name='login'),
    path('signup/', AuthorisationHandler.handle_signup, name='signup'),
    path('logout/', AuthorisationHandler.handle_logout, name='logout'),
    path('profile/<int:user_id>/', UserInterfaceHandler.handle_profile, name='user_profile'),
    path('profile/<int:user_id>/report/', report, name='report_member'),
    path('profile/edit/', UserInterfaceHandler.handle_edit_profile, name='edit'),
    path('password/', PasswordHandler.handle, name='password'),
]
