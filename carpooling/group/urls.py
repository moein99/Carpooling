from django.urls import path

from group.views import GroupManageSystem

app_name = "group"
urlpatterns = [
    path('', GroupManageSystem.handle_show_group, name="groups"),
    path('create/', GroupManageSystem.handle_create_new_group, name="groupcreate"),
    path('public/', GroupManageSystem.handle_show_public_groups, name="public"),
    path('<int:group_id>/', GroupManageSystem.handle_manage_group, name="group"),
    path('<int:group_id>/member/', GroupManageSystem.handle_get_group_members, name="group-members"),
    path('<int:group_id>/member/remove/<int:member_id>/', GroupManageSystem.handle_remove_group_members, name="remove-member"),


]
