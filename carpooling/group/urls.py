from django.urls import path

from group.views import create_group, add_member

app_name = "group"
urlpatterns = [
    path('', create_group, name="groups"),
    path('/<int:group_id>/', add_member, name="group"),
]
