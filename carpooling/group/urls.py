from django.urls import path

from group.views import GroupManageSystem

app_name = "group"
urlpatterns = [
    path('', GroupManageSystem.handel_show_group, name="groups"),
    path('create/', GroupManageSystem.handel_create_new_group, name="groupcreate"),
    path('public/', GroupManageSystem.handel_show_public_groups, name="public"),
    path('<int:group_id>/', GroupManageSystem.handel_manage_group, name="group"),
    path('<int:group_id>/member/', GroupManageSystem.handel_get_group_members, name="group-members"),
    path('<int:group_id>/member/remove/<int:member_id>/', GroupManageSystem.handel_remove_group_members, name="remove-member"),

]
