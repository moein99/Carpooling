from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden

from group.models import Group, Membership
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm
from trip.models import Trip, TripGroups


# Create your views here.
class TripHandler:
    @staticmethod
    def handle_public_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_public_trips(request)

    @staticmethod
    def do_get_public_trips(request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'show_trips.html', {'trips': trips})

    @staticmethod
    def handle_group_trips(request, group_id):
        if request.method == 'GET':
            return TripHandler.do_get_group_trips(request, group_id)

    @staticmethod
    def do_get_group_trips(request, group_id):
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return HttpResponseNotFound()

        if group.is_private:
            if request.user.is_anonymous or not request.user.is_authenticated:
                return redirect(reverse('account:login'))
            elif not Membership.objects.filter(member=request.user, group=group).exists():
                return HttpResponseForbidden()
        return render(request, 'show_trips.html', {'trips': group.trip_set.all()})

    @staticmethod
    @login_required
    def handle_categorized_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_categorized_trips(request)

    @staticmethod
    def get_user_groups(user, include_public_groups=False):
        if include_public_groups:
            if user is None:
                return Group.objects.filter(is_private=False)
            return (user.group_set.all() | Group.objects.filter(is_private=False)).distinct()
        else:
            if user is None:
                return Group.objects.none()
            return user.group_set.all()

    @staticmethod
    def do_get_categorized_trips(request):
        user = request.user
        if user.is_anonymous or not user.is_authenticated:
            user = None
        groups = TripHandler.get_user_groups(user, request.GET.get('include-public-groups') == 'true')
        return render(request, 'show_trips_categorized_by_group.html', {'groups': groups})

    @staticmethod
    @login_required(login_url='/account/login/')
    def handle_owned_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_owned_trips(request)

    @staticmethod
    def do_get_owned_trips(request):
        user = request.user
        trips = user.driving_trips.all()
        return render(request, 'show_trips.html', {'trips': trips})

    @staticmethod
    @login_required
    def handle_active_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_active_trips(request)

    @staticmethod
    def do_get_active_trips(request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'show_trips.html', {'trips': trips})

    @staticmethod
    @login_required
    def handle_available_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_available_trips(request)

    @staticmethod
    def do_get_available_trips(request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
            is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'show_available_trips.html', {'trips': trips})


DISTANCE_THRESHOLD = 100
# threshold scale: meters

user_groups_cache = {}


class TripManageSystem:
    @staticmethod
    @login_required
    def trip_creation(request):
        if request.method == 'GET':
            return render(request, 'trip_creation.html', {'form': TripForm()})
        elif request.method == 'POST':
            return TripManageSystem.handle_create(request)

    @staticmethod
    def handle_create(request_obj):
        trip_id = TripManageSystem.create_trip(request_obj)
        if trip_id:
            return redirect(reverse('trip:trip_add_groups', kwargs={'trip_id': trip_id}))
        return HttpResponseBadRequest('Invalid Request')

    @staticmethod
    def create_trip(request_obj):
        source = Point(float(request_obj.POST['source_lat']), float(request_obj.POST['source_lng']))
        destination = Point(float(request_obj.POST['destination_lat']), float(request_obj.POST['destination_lng']))
        trip_form = TripForm(data=request_obj.POST)
        if trip_form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_obj = trip_form.save(commit=False)
            trip_obj.car_provider = request_obj.user
            trip_obj.status = Trip.WAITING_STATUS
            trip_obj.source = source
            trip_obj.destination = destination
            trip_obj.save()
            return trip_obj.id
        return None

    @staticmethod
    @login_required
    def trip_add_groups(request, trip_id):
        user_nearby_groups = TripManageSystem.get_nearby_groups(request.user, trip_id)
        if request.method == 'GET':
            return render(request, "trip_add_group.html", {'groups': user_nearby_groups})
        elif request.method == 'POST':
            TripManageSystem.handle_trip_group_relation(request, trip_id, user_nearby_groups)
            return redirect(reverse("trip:trip_page", kwargs={'trip_id': trip_id}))

    @staticmethod
    def get_nearby_groups(user, trip_id):
        if (user.id, trip_id) in user_groups_cache:
            return user_groups_cache[(user.id, trip_id)]
        user_groups = user.group_set.all()
        trip = get_object_or_404(Trip, pk=trip_id)
        user_nearby_groups = []
        for group in user_groups:
            if TripManageSystem.is_group_near_trip(group, trip):
                user_nearby_groups.append(group)
        user_groups_cache[(user.id, trip_id)] = user_nearby_groups
        return user_nearby_groups

    @staticmethod
    def is_group_near_trip(group, trip):
        if group.source is not None and not (TripManageSystem.is_in_range(group.source, trip.source) or
                                             TripManageSystem.is_in_range(group.source, trip.destination)):
            return False
        return True

    @staticmethod
    def is_in_range(first_point, second_point, threshold=DISTANCE_THRESHOLD):
        return point_distance(first_point, second_point).meters <= threshold

    @staticmethod
    def handle_trip_group_relation(request_obj, trip_id, user_nearby_groups):
        trip = Trip.objects.get(id=trip_id)
        for group in user_nearby_groups:
            if request_obj.POST.get(group.code, "") == 'on':
                TripGroups.objects.create(group=group, trip=trip)

    @staticmethod
    def trip_page(request, trip_id):
        return HttpResponse("This will be trip page!")