from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from account.models import Member
from group.forms import GroupForm
from group.models import Group, Membership
from django.http import HttpResponseForbidden


class GroupManageSystem:

    @staticmethod
    @login_required
    def handle_create_new_group(request):
        if request.method == "GET":
            form = GroupForm()
        else:
            form = GroupForm(data=request.POST)
            if form.is_valid():
                instance = form.save(commit=False)
                if 'source_lat' in request.POST:
                    instance.source = Point(float(request.POST['source_lat']), float(request.POST['source_lon']))
                instance.save()
                Membership.objects.create(member=member, group=instance, role='ow')
                return redirect(reverse('group:groups'))
        return render(request, "create group.html", {
            "form": form,

        })

    @staticmethod
    @login_required
    def handle_show_group(request):
        user_owned_groups = Group.objects.filter(membership__role='ow', members=request.user).defer('description', 'source')
        user_joined_groups = Group.objects.filter(membership__role='me', members=request.user).defer('description', 'source')
        return render(request, "groups.html", {
            'user_owned_groups': user_owned_groups,
            'user_joined_groups': user_joined_groups,
        })

    @staticmethod
    @login_required
    def handle_show_public_groups(request):
        public_groups = Group.objects.filter(is_private=False)
        return render(request, "public_groups.html", {
            'public_groups': public_groups
        })

    @staticmethod
    @login_required
    def handle_manage_group(request, group_id):
        errors = []
        member, group, membership = GroupManageSystem.get_group_member_membership(request, group_id)
        if group.is_private and len(membership) == 0:
            return HttpResponseForbidden("you are not a member of this group")
        is_owner, has_joined = GroupManageSystem.manage_group_authorization(membership)
        if request.method == "POST":
            errors, has_joined = GroupManageSystem.manage_group_post(request, has_joined, is_owner, member, group,
                                                                     membership)
        return render(request, "manage_group.html", {
            'group': group,
            'is_owner': is_owner,
            'has_joined': has_joined,
            'errors': errors
        })

    @staticmethod
    def get_group_member_membership(request, group_id):
        member = get_object_or_404(Member, id=request.user.id)
        group = get_object_or_404(Group, id=group_id)
        membership = Membership.objects.filter(group_id=group.id, member_id=member.id)
        return member, group, membership

    @staticmethod
    def manage_group_authorization(membership):
        is_owner = False
        has_joined = False
        if len(membership) > 0:
            has_joined = True
            if membership[0].role == 'ow':
                is_owner = True
        return is_owner, has_joined

    @staticmethod
    def manage_group_post(request, has_joined, is_owner, member, group, membership):
        errors = []
        request_type = request.POST['type']
        if request_type == 'join' and not has_joined:
            errors.append(GroupManageSystem.join_group(member, group))
            has_joined = True
        elif request_type == 'leave' and has_joined:
            membership[0].delete()
            has_joined = False
            errors.append("you left the group")
        elif request_type == 'add' and is_owner:
            errors.append(GroupManageSystem.add_to_group(request.POST['username'], group))
        return errors, has_joined

    @staticmethod
    def add_to_group(username, group):
        member = get_object_or_404(Member, username=username)
        Membership.objects.create(member=member, group=group, role='me')
        return username + " has been added to the group"

    @staticmethod
    def join_group(member, group):
        Membership.objects.create(member=member, group=group, role='me')
        return "you have joined this group"

    @staticmethod
    @login_required
    def handle_get_group_members(request, group_id):
        member, group, membership = GroupManageSystem.get_group_member_membership(request, group_id)
        if group.is_private and len(membership) == 0:
            return HttpResponseForbidden("you are not a member of this group")
        is_owner = False
        if len(membership) and membership[0].role == 'ow':
            is_owner = True
        members = Member.objects.filter(membership__group_id=group_id).values('id', 'username', 'email')
        return render(request, "group_members.html", {
            'group': group,
            'is_owner': is_owner,
            'members': members,
        })

    @staticmethod
    @login_required
    def handle_remove_group_members(request, group_id, member_id):
        member, group, membership = GroupManageSystem.get_group_member_membership(request, group_id)
        if request.method == 'POST':
            if group.is_private and len(membership) == 0:
                return HttpResponseForbidden("you are not authorized to remove a member")
            if len(membership) and membership[0].role == 'ow':
                membership = Membership.objects.get(group_id=group.id, member_id=member_id)
                membership.delete()
                return redirect(reverse('group:group-members', kwargs={'group_id': group_id}))
            else:
                return HttpResponseForbidden("you are not authorized to remove a member")
        return redirect(reverse('group:group-members', kwargs={'group_id': group_id}))
