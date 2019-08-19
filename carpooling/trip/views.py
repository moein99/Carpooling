from datetime import datetime

import numpy as np
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseBadRequest, HttpResponseGone, HttpResponseNotAllowed, HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance
from numpy.linalg import norm

from account.models import Member
from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from root.decorators import check_request_type, only_get_allowed
from trip.forms import TripForm, TripRequestForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet, Vote
from trip.utils import extract_source, extract_destination
from .tasks import notify
from .utils import SpotifyAgent

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
    def create_trip(car_provider: Member, post_data):
        source = extract_source(post_data)
        destination = extract_destination(post_data)
        trip_form = TripForm(data=post_data)
        if trip_form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_obj = trip_form.save(commit=False)
            trip_obj.car_provider = car_provider
            trip_obj.status = Trip.WAITING_STATUS
            trip_obj.source, trip_obj.destination = source, destination
            spotify_agent = SpotifyAgent()
            trip_obj.playlist_id = spotify_agent.create_playlist(trip_obj.trip_description)
            trip_obj.save()
            TripCreationHandler.set_notification(trip_obj)
            return trip_obj
        return None

    @staticmethod
    def set_notification(trip: Trip):
        notify(trip.id, schedule=trip.start_estimation)


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
        return render(request, 'join_trip.html', {'form': TripRequestForm(user=request.user)})

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
            return redirect(reverse('trip:trip', kwargs={'pk': trip_id}))
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
        if trip.capacity > trip.passengers.count():
            trip_request = get_object_or_404(TripRequest, id=trip_request_id, trip=trip)
            if trip_request.status != TripRequest.PENDING_STATUS:
                return HttpResponseBadRequest('Request is not pending')
            trip_request.status = TripRequest.ACCEPTED_STATUS
            trip_request.save()
            Companionship.objects.create(member=trip_request.containing_set.applicant, trip=trip,
                                         source=trip_request.source, destination=trip_request.destination)
            trip_request.containing_set.close()
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


class TripDetailView(DetailView):
    model = Trip
    template_name = 'trip_page.html'

    @check_request_type
    def post(self, request, pk):
        self.object = self.get_object()
        receiver = Member.objects.get(id=int(self.request.POST['receiver_id']))
        rate = self.request.POST['rate']
        self.create_vote(receiver, rate)
        return HttpResponse("OK")

    def get_context_data(self, **kwargs):
        context = super(TripDetailView, self).get_context_data(**kwargs)
        context['is_user_in_trip'] = self.is_user_in_trip()
        context['user_request_already_sent'] = self.is_request_already_sent()
        if context['is_user_in_trip']:
            context['votes'] = self.get_votes()
        return context

    def put(self, request, pk):
        action = self.request.POST['action']
        self.object = self.get_object()
        if action == "leave":
            user_id = self.request.POST['user_id']
            self.handle_member_leaving_trip(user_id)
            return HttpResponse(str(reverse('root:home')))
        elif action == "update_status":
            self.update_status()
            return HttpResponse(str(reverse('trip:trip', kwargs={'pk': self.object.id})))
        elif action == "open_trip":
            self.open_trip()
            return HttpResponse(str(reverse('trip:trip', kwargs={'pk': self.object.id})))

    def is_user_in_trip(self):
        return self.request.user in self.object.passengers.all() or self.request.user == self.object.car_provider

    def is_request_already_sent(self):
        return TripRequest.objects.filter(trip=self.object, status=TripRequest.PENDING_STATUS,
                                          containing_set__applicant=self.request.user).exists()

    def handle_member_leaving_trip(self, user_id):
        Companionship.objects.filter(member_id=user_id, trip_id=self.object.id).delete()
        if int(user_id) == self.object.car_provider.id:
            self.handle_car_provider_leaving()

    def handle_car_provider_leaving(self):
        self.object.car_provider = None
        self.object.status = self.object.CANCELED_STATUS
        self.delete_playlist()
        self.object.save()

    def update_status(self):
        if self.object.status == self.object.WAITING_STATUS:
            self.object.status = self.object.CLOSED_STATUS
        elif self.object.status == self.object.CLOSED_STATUS:
            self.object.status = self.object.IN_ROUTE_STATUS
        elif self.object.status == self.object.IN_ROUTE_STATUS:
            self.object.status = self.object.DONE_STATUS
            self.delete_playlist()
        self.object.save()

    def open_trip(self):
        self.object.status = self.object.WAITING_STATUS
        self.object.save()

    def delete_playlist(self):
        spotify_agent = SpotifyAgent()
        spotify_agent.delete_playlist(self.object.playlist_id)
        self.object.playlist_id = None

    def get_votes(self):
        votes = {}
        vote_receivers = self.get_vote_receivers()
        for receiver in vote_receivers:
            votes[receiver] = None
        already_submitted_votes = Vote.objects.filter(receiver__in=vote_receivers, sender=self.request.user,
                                                      trip=self.object)
        for vote in already_submitted_votes:
            votes[vote.receiver] = int(vote.rate)
        return votes

    def get_vote_receivers(self):
        receivers = []
        receivers.extend(self.object.passengers.all())
        receivers.append(self.object.car_provider)
        receivers.remove(self.request.user)
        return receivers

    def create_vote(self, receiver, rate):
        Vote.objects.create(sender=self.request.user, receiver=receiver, rate=rate, trip=self.object)


class TripVoteManager(View):
    @method_decorator(login_required)
    def get(self, request, trip_id):
        members = []
        rate = []
        trip = Trip.objects.get(id=trip_id)
        members.extend(trip.passengers.all())
        members.append(trip.car_provider)
        members.remove(request.user)
        for i in range(len(members)):
            try:
                object = Vote.objects.get(sender=request.user, receiver=members[i])
                rate.append(object.rate)
            except Vote.DoesNotExist:
                rate.append(None)
        members_rate = {}
        for i in range(len(members)):
            members_rate[members[i]] = rate[i]
        return render(request, 'trip_vote_manage.html', {'members_rate': members_rate, 'trip_id': trip_id})

    @method_decorator(login_required)
    def post(self, request, trip_id):
        receiver = request.POST.get('receiver')
        rate = request.POST.get('rate')
        object = Vote(sender=request.user, receiver=Member.objects.get(id=receiver), rate=rate, trip_id=trip_id)
        object.save()
        members = []
        rate = []
        trip = Trip.objects.get(id=trip_id)
        members.extend(trip.passengers.all())
        members.append(trip.car_provider)
        members.remove(request.user)
        for i in range(len(members)):
            try:
                object = Vote.objects.get(sender=request.user, receiver=members[i])
                rate.append(object.rate)
            except Vote.DoesNotExist:
                rate.append(None)
        members_rate = {}
        for i in range(len(members)):
            members_rate[members[i]] = rate[i]
        return render(request, "trip_vote_manage.html", {'members_rate': members_rate, 'trip_id': trip_id})


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
        return redirect(reverse("trip:trip", kwargs={'pk': trip_id}))

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


class SearchTripsManger(View):
    @method_decorator(login_required)
    def get(self, request):
        if SearchTripsManger.is_valid_search_parameter(request.GET):
            return SearchTripsManger.do_search(request) if request.GET else render(request, "search_trip.html")
        return HttpResponseBadRequest()

    @staticmethod
    def subtract_two_point(point1: Point, point2: Point):
        return Point(point1.x - point2.x, point1.y - point2.y)

    @staticmethod
    def get_query_score(query, source: Point, destination: Point):
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
        source = extract_source(data)
        destination = extract_destination(data)
        trips = (request.user.driving_trips.all() | request.user.partaking_trips.all()).distinct().exclude(
            status=Trip.DONE_STATUS)
        if data['start_time'] != "-1":
            trips = SearchTripsManger.filter_by_dates(data['start_time'], data['end_time'], trips)
        trips = sorted(trips, key=lambda query: (
            SearchTripsManger.get_query_score(query, source=source, destination=destination)))
        trips = filter(lambda query: SearchTripsManger.get_query_score(query, source, destination) != np.inf, trips)
        return render(request, "trips_viewer.html", {"trips": trips})

    @staticmethod
    def is_valid_search_parameter(post_data):
        if post_data:
            return 'source_lat' in post_data and 'source_lng' in post_data and 'destination_lat' in post_data and \
                   'destination_lng' in post_data
        else:
            return True

    @staticmethod
    def filter_by_dates(start_date, end_date, trips_query_set):
        search_start_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        search_end_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        return trips_query_set.filter(start_estimation__gt=search_start_time, end_estimation__lt=search_end_time)


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


@login_required
@only_get_allowed
def get_chat_interface(request, trip_id):
    user = request.user
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.car_provider_id == user.id or Companionship.objects.filter(trip_id=trip_id, member_id=user.id).exists():
        return render(request, 'trip_chat.html', {
            'trip_id': trip_id,
            'username': user.username
        })
    else:
        return HttpResponseForbidden()
