import numpy as np
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.termcolors import background
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance
from numpy.linalg import norm

from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from trip.forms import TripForm
from trip.models import Trip, TripGroups
from trip.utils import extract_source, extract_destination

user_groups_cache = ExpiringDict(max_len=100, max_age_seconds=5 * 60)


class TripCreationHandler(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'trip_creation.html', {'form': TripForm()})

    @method_decorator(login_required)
    def post(self, request):
        trip = TripCreationHandler.create_trip(request.user, request.POST)
        if trip is not None:
            return redirect(reverse('trip:add_to_groups', kwargs={'trip_id': trip.id}))
        return HttpResponseBadRequest('Invalid Request')

    @staticmethod
    def create_trip(car_provider, post_data):
        source = extract_source(post_data)
        destination = extract_destination(post_data)
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
    def get(self, request, trip_id):
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
            if TripGroupsManager.is_group_near_trip(group, trip):
                user_nearby_groups.append(group)
        user_groups_cache[(user.id, trip_id)] = user_nearby_groups
        return user_nearby_groups

    @staticmethod
    def is_group_near_trip(group, trip):
        if group.source is not None and not (TripGroupsManager.is_in_range(group.source, trip.source) or
                                             TripGroupsManager.is_in_range(group.source, trip.destination)):
            return False
        return True

    @staticmethod
    def is_in_range(first_point, second_point, threshold=DISTANCE_THRESHOLD):
        return point_distance(first_point, second_point).meters <= threshold


class OwnedTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        trips = request.user.driving_trips.all()
        return render(request, 'trip_manager.html', {'trips': trips})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class PublicTripsManager(View):
    @staticmethod
    def get(request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'trip_manager.html', {'trips': trips})

    @staticmethod
    def post(request):
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
        group = get_object_or_404(Group, id=group_id)
        if group.is_private:
            if not Membership.objects.filter(member=request.user, group=group).exists():
                return HttpResponseForbidden()
        return render(request, 'trip_manager.html', {'trips': group.trip_set.all()})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class ActiveTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'trip_manager.html', {'trips': trips})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class AvailableTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
            is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'trip_manager.html', {'trips': trips})

    @method_decorator(login_required)
    def post(self, request):
        return HttpResponseNotAllowed('Method Not Allowed')


class SearchTripsManger(View):
    @method_decorator(login_required)
    def get(self, request):
        if SearchTripsManger.is_valid_search_parameter(request.GET):
            return SearchTripsManger.do_search(request) if request.GET else render(request, "search_trip")
        return HttpResponseBadRequest()

    @staticmethod
    def subtract_two_point(point1: Point, point2: Point):
        return Point(point1.x - point2.x, point1.y - point2.y)

    @staticmethod
    def search_sort(query, source: Point, destination: Point):
        source_to_trip_source = SearchTripsManger.subtract_two_point(query.source, source)
        destination_to_trip_destination = SearchTripsManger.subtract_two_point(query.destination, destination)
        trip_source_to_destination = SearchTripsManger.subtract_two_point(query.destination, query.source)

        if np.dot(trip_source_to_destination, SearchTripsManger.subtract_two_point(destination, source)) < 0:
            return np.inf
        else:
            if np.dot(source_to_trip_source, trip_source_to_destination) > 0:
                # distance to source dot
                to_source_distance = norm(source_to_trip_source)
            else:
                # distance to line
                to_source_distance = norm(np.cross(source_to_trip_source, trip_source_to_destination)) / norm(
                    trip_source_to_destination)

            if np.dot(destination_to_trip_destination, trip_source_to_destination) < 0:
                # distance to source dot
                to_destination_distance = norm(destination_to_trip_destination)
            else:
                # distance to line
                to_destination_distance = norm(
                    np.cross(destination_to_trip_destination, trip_source_to_destination)) / norm(
                    trip_source_to_destination)
        return to_source_distance + to_destination_distance

    @staticmethod
    def do_search(request):
        data = request.GET
        source = Point(float(data['source_lat']), float(data['source_lng']))
        destination = Point(float(data['destination_lat']), float(data['destination_lng']))
        trips = (request.user.driving_trips.all() | request.user.partaking_trips.all()).distinct().exclude(
            status=Trip.DONE_STATUS)
        trips = sorted(trips, key=lambda query: (
            SearchTripsManger.search_sort(query, source=source, destination=destination)))
        trips = filter(lambda query: SearchTripsManger.search_sort(query, source, destination) != np.inf, trips)
        return render(request,
                      "trips_viewer.html",
                      {"trips": trips}
                      )

    @staticmethod
    def is_valid_search_parameter(post_data):
        if post_data:
            return 'source_lat' in post_data and 'source_lng' in post_data and 'destination_lat' in post_data and \
                   'destination_lng' in post_data
        else:
            return True
