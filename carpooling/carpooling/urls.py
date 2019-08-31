"""carpooling URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from account import urls as account_urls
from group import urls as group_urls
from root import urls as root_urls
from trip import urls as trip_urls


class CustomLogout(auth_views.LogoutView):
    template_name = 'registration/custom_logged_out.html'


authentication_urls = [
    path('login/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', CustomLogout.as_view(), name='logout'),

    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

urlpatterns = [
                path('admin/', admin.site.urls),
                path('account/', include(account_urls, namespace='account')),
                path('account/', include(authentication_urls)),
                path('group/', include(group_urls, namespace='group')),
                path('trip/', include(trip_urls, namespace='trip')),
                path('', include(root_urls, namespace='root'))
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
