from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from account.models import Member
from group.forms import GroupForm, MembershipForm
from group.models import Group, Membership


@login_required(redirect_field_name='account:login')
def create_group(request):
    member = get_object_or_404(Member, id=request.user.id)
    if request.method == "GET":
        form = GroupForm()
    else:
        form = GroupForm(data=request.POST)
        if form.is_valid():
            instance = form.save(commit=False)

            membership_form = MembershipForm(data={
                'member': member,
                'group': instance,
                'role': 'ow'
            })
            instance.save()
            if membership_form.is_valid():
                membership_form.save()
    owned_groups = Group.objects.filter(membership__role='ow', members=member)
    joined_groups = Group.objects.filter(membership__role='me', members=member)
    return render(request, "groups.html", {
        "form": form,
        'owned_groups': owned_groups,
        'joined_groups': joined_groups,
    })
