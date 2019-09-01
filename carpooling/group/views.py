import json
import logging
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from math import radians, sin, cos, sqrt, atan2

from search import queries as search_query, index as INDEX
from account.models import Member
from group.forms import GroupForm
from group.models import Group, Membership
from group.utils import get_group_membership, add_to_group, join_group, manage_group_authorization
from root.decorators import only_get_allowed, check_request_type

log = logging.getLogger(__name__)


@login_required
@only_get_allowed
def get_user_groups_view(request):
    user_owned_groups = request.user.group_set.filter(membership__role='ow').defer('description', 'source')
    user_joined_groups = request.user.group_set.filter(membership__role='me').defer('description', 'source')
    return render(request, "groups_list.html", {
        'user_owned_groups': user_owned_groups,
        'user_joined_groups': user_joined_groups,
    })


class CreateGroupManager(View):
    @staticmethod
    def get(request):
        return render(request, "create_group.html", {
            "form": GroupForm(),
        })

    @staticmethod
    def post(request):
        form = GroupForm(data=request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            if 'source_lat' in request.POST:
                group.source = Point(float(request.POST['source_lat']), float(request.POST['source_lon']))
            group.save()
            CreateGroupManager.index_goup(group, request)
            Membership.objects.create(member=request.user, group=group, role='ow')
            log.info("user:{} made group:{}".format(request.user.id, group.id))
            return redirect(reverse('group:groups_list'))
        return render(request, "create_group.html", {
            "form": form,
        })

    @staticmethod
    def index_goup(group, request):
        if 'source_lat' in request.POST:
            data_map = {
                "pin": {
                    "location": {
                        'lat': request.POST['source_lat'],
                        'lon': request.POST['source_lon']
                    }
                },
            }
            INDEX.index_group_map(data_map, group.id, schedule=1)

        data = {
            "id": group.id,
            "code": group.code,
            "title": group.title,
            "description": group.description
        }
        INDEX.index_group(data, schedule=1)
        log.info("group:{} was added to elastic search".format(request.user.id, group.id))


@login_required
@only_get_allowed
def get_public_groups_view(request):
    public_groups = Group.objects.filter(is_private=False)
    return render(request, "public_groups.html", {
        'public_groups': public_groups
    })


# TODO: Clean this! It's dirty
class GroupManager(View):
    @staticmethod
    def get(request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponse("You are not a member of this group", status=403)
        is_owner, has_joined = manage_group_authorization(membership)
        return render(request, "manage_group.html", {
            'group': group,
            'is_owner': is_owner,
            'has_joined': has_joined,
        })

    @staticmethod
    def post(request, group_id):
        errors = []
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponse("You are not a member of this group", status=403)
        is_owner, has_joined = manage_group_authorization(membership)
        request_action = request.POST['action']
        if request_action == 'join' and not has_joined:
            log.info("user:{} joined group:{}".format(request.user.id, group_id))
            errors.append(join_group(request.user, group))
            has_joined = True
        elif request_action == 'leave' and has_joined:
            log.info("user:{} left group:{}".format(request.user.id, group_id))
            membership.delete()
            has_joined = False
            errors.append("you left the group")
        elif request_action == 'add' and is_owner:
            log.info("user:{} added user:{} to group:{}".format(request.user.id, request.POST['username'], group_id))
            errors.append(add_to_group(request.POST['username'], group))

        return render(request, "manage_group.html", {
            'group': group,
            'is_owner': is_owner,
            'has_joined': has_joined,
            'errors': errors
        })


# TODO: Clean this! It's dirty
class GroupMembersManager(View):
    @staticmethod
    def get(request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        if group.is_private and membership is None:
            return HttpResponse("you are not a member of this group", status=403)
        is_owner = False
        if membership and membership.role == 'ow':
            is_owner = True
        members = Member.objects.filter(membership__group_id=group_id).values('id', 'username', 'email')
        return render(request, "group_members.html", {
            'group': group,
            'is_owner': is_owner,
            'members': members,
        })

    @check_request_type
    def post(self, request, group_id):
        return HttpResponse('Method Not Allowed', status=405)

    @staticmethod
    def delete(request, group_id):
        group, membership = get_group_membership(request.user, group_id)
        member_id = request.POST.get('member_id', None)
        if group.is_private and membership is None:
            return HttpResponse("You are not authorized to remove a member", status=403)
        if membership and membership.role == 'ow':
            log.info("user:{} removed user:{} from group:{}".format(request.user.id, member_id, group_id))
            get_object_or_404(Membership, group_id=group.id, member_id=member_id).delete()
            return redirect(reverse('group:group_members', kwargs={'group_id': group_id}))
        return HttpResponse("You are not authorized to remove a member", status=403)


class SearchGroupManager:
    @classmethod
    @method_decorator(login_required)
    def search_group_view(cls, request, query):
        log.info("user {} searched for groups with containing:{}".format(request.user.id, query))
        result = {'groups': []}
        for group in search_query.group_search_with_out_map(query)['hits']['hits']:

            instance = get_object_or_404(Group, id=group["_source"]["id"])
            if not instance.is_private or Membership.objects.filter(member=request.user, group_id=instance.id).exists():
                result['groups'].append(SearchGroupManager.get_group_json(instance))
        return HttpResponse(json.dumps(result))

    @staticmethod
    def get_group_json(group):
        return {'title': group.title, 'description': group.description + " " + group.code,
                'url': reverse('group:group', kwargs={'group_id': group.id})}


@login_required
@only_get_allowed
def sort(request):
    data = {
        "lat": float(request.GET['source_lat']),
        "lon": float(request.GET['source_lon'])
    }
    log.info("user {} searched near by groups to lat:{} lon:{}".format(request.user.id, data["lat"], data["lon"]))
    group_list = []
    for group in search_query.group_search_with_map(data)['hits']['hits']:
        instance = get_object_or_404(Group, id=group['_id'])
        if not instance.is_private or Membership.objects.filter(member=request.user, group=instance).exists():
            group_list.append(instance)
    return render(request, "sorted_group_list.html", {"group_list": group_list})
