import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from account.models import Member
from group.forms import GroupForm
from group.models import Group, Membership
from group.utils import get_group_membership, add_to_group, join_group, manage_group_authorization


class UserGroupsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user_owned_groups = request.user.group_set.filter(membership__role='ow').defer('description', 'source')
        user_joined_groups = request.user.group_set.filter(membership__role='me').defer('description', 'source')
        return render(request, "groups_list.html", {
            'user_owned_groups': user_owned_groups,
            'user_joined_groups': user_joined_groups,
        })


class CreateGroupManager(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, "create_group.html", {
            "form": GroupForm(),
        })

    @method_decorator(login_required)
    def post(self, request):
        form = GroupForm(data=request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            if 'source_lat' in request.POST:
                instance.source = Point(float(request.POST['source_lat']), float(request.POST['source_lon']))
            instance.save()
            Membership.objects.create(member=request.user, group=instance, role='ow')
            return redirect(reverse('group:groups_list'))
        return render(request, "create_group.html", {
            "form": form,
        })


class PublicGroupsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        public_groups = Group.objects.filter(is_private=False)
        return render(request, "public_groups.html", {
            'public_groups': public_groups
        })


# TODO: Clean this! It's dirty
class GroupManager(View):
    @method_decorator(login_required)
    def get(self, request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponseForbidden("You are not a member of this group")
        is_owner, has_joined = manage_group_authorization(membership)
        return render(request, "manage_group.html", {
            'group': group,
            'is_owner': is_owner,
            'has_joined': has_joined,
        })

    @method_decorator(login_required)
    def post(self, request, group_id):
        errors = []
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponseForbidden("You are not a member of this group")
        is_owner, has_joined = manage_group_authorization(membership)
        request_action = request.POST['action']
        if request_action == 'join' and not has_joined:
            errors.append(join_group(request.user, group))
            has_joined = True
        elif request_action == 'leave' and has_joined:
            membership.delete()
            has_joined = False
            errors.append("you left the group")
        elif request_action == 'add' and is_owner:
            errors.append(add_to_group(request.POST['username'], group))

        return render(request, "manage_group.html", {
            'group': group,
            'is_owner': is_owner,
            'has_joined': has_joined,
            'errors': errors
        })


# TODO: Clean this! It's dirty
class GroupMembersManager(View):
    @method_decorator(login_required)
    def get(self, request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponseForbidden("you are not a member of this group")
        is_owner = False
        if membership and membership.role == 'ow':
            is_owner = True
        members = Member.objects.filter(membership__group_id=group_id).values('id', 'username', 'email')
        return render(request, "group_members.html", {
            'group': group,
            'is_owner': is_owner,
            'members': members,
        })

    @method_decorator(login_required)
    def post(self, request, group_id):
        if request.POST.get('type') == 'DELETE':
            return self.delete(request, group_id)
        return HttpResponseNotAllowed('Method Not Allowed')

    @method_decorator(login_required)
    def delete(self, request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        member_id = request.POST.get('member_id', None)
        if group.is_private and membership is None:
            return HttpResponseForbidden("You are not authorized to remove a member")
        if membership and membership.role == 'ow':
            get_object_or_404(Membership, group_id=group.id, member_id=member_id).delete()
            return redirect(reverse('group:group_members', kwargs={'group_id': group_id}))
        return HttpResponseForbidden("You are not authorized to remove a member")


class SearchGroupManager:
    @staticmethod
    @login_required
    def search_group_view(request, query):
        result = {'groups': []}
        for group in Group.objects.all():
            if query in group.title:
                result['groups'].append(SearchGroupManager.get_group_json(group))
        return HttpResponse(json.dumps(result))

    @staticmethod
    def get_group_json(group):
        return {'title': group.title, 'description': group.description,
                'url': reverse('group:group', kwargs={'group_id': group.id})}
