from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from group.models import Group, Membership
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm
from trip.models import Trip, TripGroups
from expiringdict import ExpiringDict

user_groups_cache = ExpiringDict(max_len=100, max_age_seconds=5*60)

DISTANCE_THRESHOLD = 100  # threshold scale: meters
# Create your views here.


class TripCreationHandler(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'trip_creation.html', {'form': TripForm()})

    @method_decorator(login_required)
    def post(self, request):
        trip = TripHandler.create_trip(request.user, request.POST)
        if trip is not None:
            return redirect(reverse('trip:add-to-groups', kwargs={'trip_id': trip.id}))
        return HttpResponseBadRequest('Invalid Request')

    @staticmethod
    def create_trip(car_provider, post_data):
        source = Point(float(post_data['source_lat']), float(post_data['source_lng']))
        destination = Point(float(post_data['destination_lat']), float(post_data['destination_lng']))
        trip_form = TripForm(data=post_data)
        if trip_form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_obj = trip_form.save(commit=False)
            trip_obj.car_provider = car_provider
            trip_obj.status = Trip.WAITING_STATUS
            trip_obj.source, trip_obj.destination = source, destination
            trip_obj.save()
            return trip_obj
        return None


class TripHandler(View):
    @method_decorator(login_required)
    def get(self, request):
        raise NotImplementedError()

    @method_decorator(login_required)
    def post(self, request):
        raise NotImplementedError()


class TripGroupsManager(View):
    @method_decorator(login_required)
    def get(self, request, trip_id):
        user_nearby_groups = TripGroupsManager.get_nearby_groups(request.user, trip_id)
        return render(request, "trip_add_to_groups.html", {'groups': user_nearby_groups})

    @method_decorator(login_required)
    def post(self, request, trip_id):
        user_nearby_groups = TripGroupsManager.get_nearby_groups(request.user, trip_id)
        trip = Trip.objects.get(id=trip_id)
        for group in user_nearby_groups:
            if request.POST.get(group.code, None) == 'on':
                TripGroups.objects.create(group=group, trip=trip)
        return redirect(reverse("trip:trip", kwargs={'trip_id': trip_id}))

    @staticmethod
    def get_nearby_groups(user, trip_id):
        user_nearby_groups = user_groups_cache.get((user.id, trip_id))
        if user_nearby_groups is not None:
            return user_groups_cache[(user.id, trip_id)]
        user_groups = user.group_set.all()
        trip = get_object_or_404(Trip, id=trip_id)
        user_nearby_groups = []
        for group in user_groups:
            if TripHandler.is_group_near_trip(group, trip):
                user_nearby_groups.append(group)
        user_groups_cache[(user.id, trip_id)] = user_nearby_groups
        return user_nearby_groups


class OwnedTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        trips = request.user.driving_trips.all()
        return render(request, 'trip_manager.html', {'trips': trips})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class PublicTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'trip_manager.html', {'trips': trips})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class CategorizedTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        include_public_groups = request.GET.get('include-public-groups') == 'true'
        if include_public_groups:
            groups = (user.group_set.all() | Group.objects.filter(is_private=False)).distinct()
        else:
            groups = user.group_set.all()
        return render(request, 'trips_categorized_by_group.html', {'groups': groups})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class GroupTripsManager(View):
    @method_decorator(login_required)
    def get(self, request, group_id):
        group = Group.objects.get_or_404(id=group_id)
        if group.is_private:
            if not request.user.is_authenticated:
                return redirect(reverse('account:login'))
            elif not Membership.objects.filter(member=request.user, group=group).exists():
                return HttpResponseForbidden()
        return render(request, 'trip_manager.html', {'trips': group.trip_set.all()})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')





class TripHandler:

    @staticmethod
    def is_group_near_trip(group, trip):
        if group.source is not None and not (TripHandler.is_in_range(group.source, trip.source) or
                                             TripHandler.is_in_range(group.description, trip.destination)):
            return False
        return True

    @staticmethod
    def is_in_range(first_point, second_point, threshold=DISTANCE_THRESHOLD):
        return point_distance(first_point, second_point).meters <= threshold


    @staticmethod
    @login_required
    def handle_owned_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_owned_trips(request)

    @staticmethod
    def do_get_owned_trips(request):
        user = request.user
        trips = user.driving_trips.all()
        return render(request, 'trip_manager.html', {'trips': trips})

    @staticmethod
    @login_required
    def handle_active_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_active_trips(request)

    @staticmethod
    def do_get_active_trips(request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'trip_manager.html', {'trips': trips})

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
        return render(request, 'trip_manager.html', {'trips': trips})
