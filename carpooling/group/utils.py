from django.shortcuts import get_object_or_404

from account.models import Member
from group.models import Membership, Group


def get_group_membership(user, group_id):
    group = get_object_or_404(Group, id=group_id)
    try:
        membership = Membership.objects.get(group_id=group.id, member_id=user.id)
    except Membership.DoesNotExist:
        membership= None
    return group, membership


def manage_group_authorization(membership):
    is_owner = False
    has_joined = False
    if membership:
        has_joined = True
        if membership.role == 'ow':
            is_owner = True
    return is_owner, has_joined


def add_to_group(username, group):
    member = get_object_or_404(Member, username=username)
    Membership.objects.create(member=member, group=group, role='me')
    return username + " has been added to the group"


def join_group(member, group):
    Membership.objects.create(member=member, group=group, role='me')
    return "you have joined this group"
