from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseBadRequest, HttpResponseGone, HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance

from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from root.decorators import check_request_type, only_get_allowed
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
    def get(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if trip.status != trip.WAITING_STATUS:
            return HttpResponseGone('Trip status is not waiting')
        if request.user == trip.car_provider:
            return self.show_trip_requests(request, trip)
        else:
            return self.show_create_request_form(request, trip)

    @staticmethod
    def show_trip_requests(request, trip, error=None):
        trip_members_count = Companionship.objects.filter(trip=trip).count()
        return render(request, 'trip_requests.html', {
            'requests': trip.requests.filter(status=TripRequest.PENDING_STATUS),
            'members_count': trip_members_count,
            'capacity': trip.capacity,
            'error': error,
        })

    @staticmethod
    def show_create_request_form(request, trip):
        if trip.capacity > trip.passengers.count():
            return render(request, 'join_trip.html', {'form': TripRequestForm(user=request.user)})
        return HttpResponseGone('Trip is full')

    @check_request_type
    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user == trip.car_provider:
            return HttpResponseForbidden()

        if trip.status != trip.WAITING_STATUS:
            return HttpResponseGone('Trip status is not waiting')

        source = extract_source(request.POST)
        destination = extract_destination(request.POST)
        form = TripRequestForm(user=request.user, trip=trip, data=request.POST)
        if form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            TripRequestManager.create_trip_request(form, source, destination)
            return redirect(reverse('trip:trip', kwargs={'trip_id': trip_id}))
        return render(request, 'join_trip.html', {'form': form})

    @staticmethod
    def create_trip_request(form, source, destination):
        if form.cleaned_data['create_new_request_set']:
            request_set = TripRequestSet.objects.create(applicant=form.user,
                                                        title=form.cleaned_data['new_request_set_title'])
        else:
            request_set = form.cleaned_data['containing_set']
        trip_request = form.save(commit=False)
        trip_request.source, trip_request.destination = source, destination
        trip_request.containing_set = request_set
        trip_request.trip = form.trip
        trip_request.save()
        return trip_request

    def put(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user != trip.car_provider:
            return HttpResponseForbidden()

        if trip.status != trip.WAITING_STATUS:
            return HttpResponseGone('Trip status is not waiting')

        try:
            trip_request_id = int(request.POST.get('request_id'))
        except (ValueError, TypeError):
            return HttpResponseBadRequest()

        # TODO: change the following line to "action = request.POST.get('action')" and handle action field in template
        action = request.POST.get('action', 'accept')
        if action == 'accept':
            return TripRequestManager.accept_request_if_trip_is_not_full(request, trip, trip_request_id)
        elif action == 'decline':
            return TripRequestManager.decline_request(request, trip, trip_request_id)
        else:
            return HttpResponseBadRequest('Unknown action')

    @staticmethod
    @atomic
    def accept_request_if_trip_is_not_full(request, trip, trip_request_id):
        if trip.capacity > Companionship.objects.filter(trip=trip).count():
            trip_request = get_object_or_404(TripRequest, id=trip_request_id, trip=trip)
            if trip_request.status != TripRequest.PENDING_STATUS:
                return HttpResponseBadRequest('Request is not pending')
            trip_request.status = TripRequest.ACCEPTED_STATUS
            trip_request.save()
            Companionship.objects.create(member=trip_request.containing_set.applicant, trip=trip,
                                         source=trip_request.source, destination=trip_request.destination)
            trip_request.containing_set.close()
            trip_request.containing_set.save()
            return TripRequestManager.show_trip_requests(request, trip)
        return TripRequestManager.show_trip_requests(request, trip, "Trip is full")

    @staticmethod
    @atomic
    def decline_request(request, trip, trip_request_id):
        trip_request = get_object_or_404(TripRequest, id=trip_request_id, trip=trip)
        if trip_request.status != TripRequest.PENDING_STATUS:
            return HttpResponseBadRequest('Request is not pending')
        trip_request.status = TripRequest.DECLINED_STATUS
        trip_request.save()
        return TripRequestManager.show_trip_requests(request, trip)


class TripHandler(View):
    @method_decorator(login_required)
    def get(self, request, trip_id):
        return HttpResponse('Not Implemented yet')

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


@login_required
@only_get_allowed
def get_owned_trips_view(request):
    trips = request.user.driving_trips.all()
    return render(request, 'trip_manager.html', {'trips': trips})


@only_get_allowed
def get_public_trips_view(request):
    trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
    return render(request, 'trip_manager.html', {'trips': trips})


@login_required
@only_get_allowed
def get_categorized_trips_view(request):
    user = request.user
    include_public_groups = request.GET.get('include-public-groups') == 'true'
    if include_public_groups:
        groups = (user.group_set.all() | Group.objects.filter(is_private=False)).distinct()
    else:
        groups = user.group_set.all()
    return render(request, 'trips_categorized_by_group.html', {'groups': groups})


@login_required
@only_get_allowed
def get_group_trips_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if group.is_private:
        if not Membership.objects.filter(member=request.user, group=group).exists():
            return HttpResponseForbidden()
    return render(request, 'trip_manager.html', {'trips': group.trip_set.all()})


@login_required
@only_get_allowed
def get_active_trips_view(request):
    user = request.user
    trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
    return render(request, 'trip_manager.html', {'trips': trips})


@login_required
@only_get_allowed
def get_available_trips_view(request):
    user = request.user
    trips = (user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
        is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)
    return render(request, 'trip_manager.html', {'trips': trips})
