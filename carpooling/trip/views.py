import numpy as np
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed
from numpy.linalg import norm

from group.models import Group, Membership
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm
from trip.models import Trip, TripGroups
from expiringdict import ExpiringDict

user_groups_cache = ExpiringDict(max_len=100, max_age_seconds=5 * 60)

DISTANCE_THRESHOLD = 100  # threshold scale: meters


# Create your views here.
class TripHandler:
    @staticmethod
    @login_required
    def handle_create_trip(request):
        if request.method == 'GET':
            return TripHandler.do_get_create_trip(request)
        elif request.method == 'POST':
            return TripHandler.do_post_create_trip(request)

    @staticmethod
    def do_get_create_trip(request):
        return render(request, 'trip_creation.html', {'form': TripForm()})

    @staticmethod
    def do_post_create_trip(request):
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

    @staticmethod
    def handle_trip(request, trip_id):
        raise NotImplementedError()

    @staticmethod
    @login_required
    def handle_add_to_groups(request, trip_id):
        user_nearby_groups = TripHandler.get_nearby_groups(request.user, trip_id)
        if request.method == 'GET':
            return TripHandler.do_get_add_to_groups(request, user_nearby_groups)
        elif request.method == 'POST':
            return TripHandler.do_post_add_to_groups(request, trip_id, user_nearby_groups)

    @staticmethod
    def do_get_add_to_groups(request, user_nearby_groups):
        return render(request, "trip_add_to_groups.html", {'groups': user_nearby_groups})

    @staticmethod
    def do_post_add_to_groups(request, trip_id, user_nearby_groups):
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
    def handle_public_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_public_trips(request)

    @staticmethod
    def do_get_public_trips(request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'trip_manager.html', {'trips': trips})

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
        return render(request, 'trip_manager.html', {'trips': group.trip_set.all()})

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
        return render(request, 'trips_categorized_by_group.html', {'groups': groups})

    @staticmethod
    @login_required(login_url='/account/login/')
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

    @staticmethod
    @login_required
    def handle_search_trip(request):
        if request.method == "GET":
            if TripHandler.is_valid_search_parameter(request.GET):
                if request.GET:
                    return TripHandler.do_search(request)
                else:
                    return render(request, "search_trip")
            else:
                return HttpResponseBadRequest()
        else:
            return HttpResponseNotAllowed()

    @staticmethod
    def substrak_two_point(point1: Point, point2: Point):
        return Point(point1.x - point2.x, point1.y - point2.y)

    @staticmethod
    def search_sort(query, source: Point, destination: Point):
        source_to_trip_source = TripHandler.substrak_two_point(query.source, source)
        destination_to_trip_destination = TripHandler.substrak_two_point(query.destination, destination)
        trip_source_to_destination = TripHandler.substrak_two_point(query.destination, query.source)

        if np.dot(trip_source_to_destination, TripHandler.substrak_two_point(destination, source)) < 0:
            return 360 + 360
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
        post_data = request.GET
        source = Point(float(post_data['source_lat']), float(post_data['source_lng']))
        destination = Point(float(post_data['destination_lat']), float(post_data['destination_lng']))
        trips = (request.user.driving_trips.all() | request.user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        trips = sorted(trips, key=lambda query: (TripHandler.search_sort(query, source=source, destination=destination)))[:5]
        print("trip source = ", source, destination)
        for trip in trips:
            print(TripHandler.search_sort(trip, source, destination))
            print(trip.source.x)
            print(trip.source.y)
        print(len(trips))
        return render(request,
                      "trips_viewer.html",
                      {"trips": trips}
                      )

    @staticmethod
    def is_valid_search_parameter(post_data):
        if post_data:
            return 'source_lat' in post_data and 'source_lng' in post_data and 'destination_lat' in post_data and 'destination_lng' in post_data
        else:
            return True
