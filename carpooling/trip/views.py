from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
# Create your views here.
from django.urls import reverse
from account.models import Member
from group.models import Group
from trip.forms import TripForm
from trip.models import Trip


def trip_init(request):
    return render(request, 'trip_manager.html', {})


@login_required()
def trip_creation(request):
    if request.method == 'GET':
        return render(request, 'trip_creation.html', {'form': TripForm(), 'groups': get_user_groups(request.user.id)})
    elif request.method == 'POST':
        return handle_create(request)


def handle_create(request_obj):
    trip_form = TripForm(data=request_obj.POST)
    if trip_form.is_valid():
        trip_form = trip_form.save(commit=False)
        trip_form.car_provider = Member.objects.get(id=request_obj.user.id)
        trip_form.status = Trip.WAITING_STATUS
        trip_form.source = Point(float(request_obj.POST['source_lat']), float(request_obj.POST['source_lng']))
        trip_form.destination = Point(float(request_obj.POST['destination_lat']),
                                      float(request_obj.POST['destination_lng']))
        trip_form.save()
        return redirect(reverse('trip:trip_init'))
    else:
        return HttpResponseBadRequest('Invalid Request')


def get_user_groups(user_id):
    groups = Group.objects.filter(membership__member_id=user_id)
    groups_dict = {}
    for group in groups:
        groups_dict[group.title] = group.code
    return groups_dict
