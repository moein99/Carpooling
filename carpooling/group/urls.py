from django.urls import path

from group.views import GroupManageSystem

app_name = "group"
urlpatterns = [
    path('', GroupManageSystem.show_group, name="groups"),
    path('<int:group_id>/', GroupManageSystem.manage_group , name="group"),
    path('create/', GroupManageSystem.create_new_group, name="groupcreate"),
    path('public/', GroupManageSystem.show_public_groups, name="public"),
    path('<int:group_id>/members/', GroupManageSystem.get_group_members, name="group-members"),
    path('<int:group_id>/members/remove/<int:member_id>/', GroupManageSystem.remove_group_members, name="remove-member"),

]
