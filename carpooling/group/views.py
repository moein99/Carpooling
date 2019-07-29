from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from account.models import Member
from group.forms import GroupForm, MembershipForm
from group.models import Group


def create_new_group(request, member):
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
    return form


@login_required(redirect_field_name='account:login')
def create_group(request):
    member = get_object_or_404(Member, id=request.user.id)
    if request.method == "GET":
        form = GroupForm()
    else:
        form = create_new_group(request, member)
    user_owned_groups = Group.objects.filter(membership__role='ow', members=member).defer('description', 'source_lat',
                                                                                          'source_lon')
    user_joined_groups = Group.objects.filter(membership__role='me', members=member).defer('description', 'source_lat',
                                                                                           'source_lon')
    return render(request, "groups.html", {
        "form": form,
        'user_owned_groups': user_owned_groups,
        'user_joined_groups': user_joined_groups,
    })


def add_member(request):
    pass
