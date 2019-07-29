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
from django.urls import path, include
from account import urls as account_urls
from group import urls as group_urls
from trip import urls as trip_urls
from root import urls as root_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/', include(account_urls, namespace='account')),
    path('group/', include(group_urls, namespace='group')),
    path('trip/', include(trip_urls, namespace='trip')),
    path('', include(root_urls, namespace='root'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
