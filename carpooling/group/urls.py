from django.urls import path

from group.views import add_member, group, create_new_group

app_name = "group"
urlpatterns = [
    path('', group, name="groups"),
    path('<int:group_id>/', add_member, name="group"),
    path('create/', create_new_group, name="groupcreate"),
]
