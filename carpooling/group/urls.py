from django.urls import path

from group.views import UserGroupsManager, CreateGroupManager, PublicGroupsManager, GroupManager, \
    GroupMembersManager

app_name = "group"
urlpatterns = [
    path('', UserGroupsManager.as_view(), name="groups_list"),
    path('create/', CreateGroupManager.as_view(), name="create_group"),
    path('public/', PublicGroupsManager.as_view(), name="public_groups"),
    path('<int:group_id>/', GroupManager.as_view(), name="group"),
    path('<int:group_id>/member/', GroupMembersManager.as_view(), name="group_members"),
]
