from django.contrib.auth.decorators import login_required
from django.urls import path

from group.views import CreateGroupManager, GroupManager, \
    GroupMembersManager, SearchGroupManager, sort, get_user_groups_view, get_public_groups_view

app_name = "group"

urlpatterns = [
    path('', get_user_groups_view, name="groups_list"),
    path('create/', login_required(CreateGroupManager.as_view()), name="create_group"),
    path('public/', get_public_groups_view, name="public_groups"),
    path('<int:group_id>/', login_required(GroupManager.as_view()), name="group"),
    path('<int:group_id>/member/', login_required(GroupMembersManager.as_view()), name="group_members"),
    path('search/<query>', SearchGroupManager.search_group_view, name="group_search"),
    path('nearby-groups/', sort, name="nearby_groups")]
