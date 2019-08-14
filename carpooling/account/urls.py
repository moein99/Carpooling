from django.urls import path
from account.views.mail import MailManager
from account.views.profile import SignUp, UserProfileManager
from account.views.report import ReportManager

app_name = "account"
urlpatterns = [
    path('signup/', SignUp.as_view(), name='signup'),
    path('profile/<int:user_id>/', UserProfileManager.as_view(), name='user_profile'),
    path('profile/<int:user_id>/report/', ReportManager.as_view(), name='report_user'),
    path('mail/', MailManager.as_view(), name='user_inbox'),
]
