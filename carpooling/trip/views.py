from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance
from .utils import SpotifyAgent
from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from trip.forms import TripForm
from trip.models import Trip, TripGroups

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
        source = Point(float(post_data['source_lat']), float(post_data['source_lng']))
        destination = Point(float(post_data['destination_lat']), float(post_data['destination_lng']))
        trip_form = TripForm(data=post_data)
        if trip_form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_obj = trip_form.save(commit=False)
            trip_obj.car_provider = car_provider
            trip_obj.status = Trip.WAITING_STATUS
            trip_obj.source, trip_obj.destination = source, destination
            spotify_agent = SpotifyAgent()
            trip_obj.playlist_id = spotify_agent.create_playlist(trip_obj.trip_description)
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


class MusicPlayerManager(View):
    def get(self, request, trip_id):
        playlist_id = Trip.objects.get(id=trip_id).playlist_id
        return render(request, 'music_player.html', {"playlist_id": playlist_id, 'trip_id': trip_id})
