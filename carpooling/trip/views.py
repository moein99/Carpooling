from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance

from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from trip.forms import TripForm, TripRequestForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet
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


class TripRequestManager(View):
    @method_decorator(login_required)
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user == trip.car_provider:
            return TripRequestManager.show_trip_requests(request, trip)
        else:
            return render(request, 'join_trip.html', {'form': TripRequestForm(user=request.user)})

    @staticmethod
    def show_trip_requests(request, trip, error=None):
        trip_members_count = Companionship.objects.filter(trip=trip).count()
        return render(request, 'trip_requests.html', {
            'requests': trip.requests.filter(status=TripRequest.PENDING_STATUS),
            'members_count': trip_members_count,
            'capacity': trip.capacity,
            'error': error,
        })

    @method_decorator(login_required)
    def post(self, request, trip_id):
        type = request.POST.get('type', 'POST')
        if type == 'PUT':
            return self.put(request, trip_id)
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user == trip.car_provider:
            return HttpResponseForbidden()
        source = extract_source(request.POST)
        destination = extract_destination(request.POST)
        form = TripRequestForm(user=request.user, trip=trip, data=request.POST)
        if form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_request = TripRequestManager.create_trip_request(form, source, destination)
            return redirect(reverse('trip:trip', kwargs={'trip_id': trip_id}))
        else:
            return render(request, 'join_trip.html', {'form': form})

    @staticmethod
    def create_trip_request(form, source, destination):
        if form.cleaned_data['create_new_request_set']:
            request_set = TripRequestSet.objects.create(applicant=form.user, title=form.cleaned_data['title'])
        else:
            request_set = form.cleaned_data['containing_set']
        trip_request = form.save(commit=False)
        trip_request.source, trip_request.destination = source, destination
        trip_request.containing_set = request_set
        trip_request.trip = form.trip
        trip_request.save()
        return trip_request

    @method_decorator(login_required)
    def put(self, request, trip):
        if request.user != trip.car_provider:
            return HttpResponseForbidden()
        try:
            trip_request_id = int(request.POST.get('request_id'))
        except (ValueError, TypeError):
            return HttpResponseBadRequest()
        return TripRequestManager.accept_request_if_trip_is_not_full(request, trip, trip_request_id)

    @staticmethod
    @atomic
    def accept_request_if_trip_is_not_full(request, trip, trip_request_id):
        if trip.capacity > Companionship.objects.filter(trip=trip).count():
            trip_request = get_object_or_404(TripRequest, id=trip_request_id)
            trip_request.status = TripRequest.ACCEPTED_STATUS
            trip_request.save()
            trip_request.containing_set.close()
            return TripRequestManager.show_trip_requests(request, trip)
        return TripRequestManager.show_trip_requests(request, trip, "trip is full")


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


class PublicTripsManager(View):
    @staticmethod
    def get(request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'trip_manager.html', {'trips': trips})


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


class GroupTripsManager(View):
    @method_decorator(login_required)
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if group.is_private:
            if not Membership.objects.filter(member=request.user, group=group).exists():
                return HttpResponseForbidden()
        return render(request, 'trip_manager.html', {'trips': group.trip_set.all()})


class ActiveTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'trip_manager.html', {'trips': trips})


class AvailableTripsManager(View):
    @method_decorator(login_required)
    def get(self, request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
            is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)
        return render(request, 'trip_manager.html', {'trips': trips})
