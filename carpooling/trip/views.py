from datetime import datetime
from django.utils import timezone

import numpy as np
from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseBadRequest, HttpResponseGone
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance

from account.forms import MailForm
from account.models import Member
from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from root.decorators import check_request_type, only_get_allowed
from trip.forms import TripForm, TripRequestForm, AutomaticJoinTripForm, QuickMailForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet
from trip.utils import extract_source, extract_destination, get_trip_score, CAR_PROVIDER_QUICK_MESSAGES, \
    PASSENGER_QUICK_MESSAGES
from trip.forms import TripForm, TripRequestForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet, Vote
from trip.utils import extract_source, extract_destination
from .tasks import notify
from .utils import SpotifyAgent

user_groups_cache = ExpiringDict(max_len=100, max_age_seconds=5 * 60)


class TripCreationManger(View):
    @staticmethod
    def get(request):
        return render(request, 'trip_creation.html', {'form': TripForm()})

    @classmethod
    def post(cls, request):
        trip = cls.create_trip(request.user, request.POST)
        if trip is not None:
            return redirect(reverse('trip:add_to_groups', kwargs={'trip_id': trip.id}))
        return HttpResponseBadRequest('Invalid Request')

    @classmethod
    def create_trip(cls, car_provider: Member, post_data):
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
            cls.set_notification(trip_obj)
            return trip_obj
        return None

    @staticmethod
    def set_notification(trip: Trip):
        notify(trip.id, schedule=trip.start_estimation)


class TripRequestManager(View):
    @classmethod
    def get(cls, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)

        if request.user == trip.car_provider:
            if trip.status != trip.WAITING_STATUS:
                return HttpResponseGone('Trip status is not waiting')
            return cls.show_trip_requests(request, trip)

        elif trip in Trip.get_accessible_trips_for(request.user):
            if trip.status != trip.WAITING_STATUS:
                return HttpResponseGone('Trip status is not waiting')
            return cls.show_create_request_form(request)
        else:
            return HttpResponseForbidden('You have not access to this trip')

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
    def show_create_request_form(request):
        return render(request, 'join_trip.html', {'form': TripRequestForm(user=request.user)})

    @check_request_type
    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user == trip.car_provider:
            return HttpResponseForbidden()

        if trip not in Trip.get_accessible_trips_for(request.user):
            return HttpResponseForbidden('You have not access to this trip')

        if trip.status != trip.WAITING_STATUS:
            return HttpResponseGone('Trip status is not waiting')

        source = extract_source(request.POST)
        destination = extract_destination(request.POST)
        form = TripRequestForm(user=request.user, trip=trip, data=request.POST)
        if form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_request = TripRequestManager.create_trip_request(form, source, destination)
            if trip.people_can_join_automatically:
                try:
                    self.accept_trip_request(trip, trip_request.id)
                except Trip.TripIsFullException():
                    pass
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

    @classmethod
    def put(cls, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user != trip.car_provider:
            return HttpResponseForbidden()

        if trip.status != trip.WAITING_STATUS:
            return HttpResponseGone('Trip status is not waiting')

        try:
            trip_request_id = int(request.POST.get('request_id'))
        except (ValueError, TypeError):
            return HttpResponseBadRequest()

        # TODO: Handle action field in template
        action = request.POST.get('action')
        if action == 'accept':
            try:
                cls.accept_trip_request(trip, trip_request_id)
                return cls.show_trip_requests(request, trip)
            except Trip.TripIsFullException:
                return cls.show_trip_requests(request, trip, "Trip is full")
        elif action == 'decline':
            cls.decline_request(trip, trip_request_id)
            return cls.show_trip_requests(request, trip)
        else:
            return HttpResponseBadRequest('Unknown action')

    @staticmethod
    @atomic
    def accept_trip_request(trip, trip_request_id):
        if trip.capacity <= trip.passengers.count():
            raise Trip.TripIsFullException()
        trip_request = get_object_or_404(TripRequest, id=trip_request_id, trip=trip)
        trip_request.status = TripRequest.ACCEPTED_STATUS
        trip_request.save()
        Companionship.objects.create(member=trip_request.containing_set.applicant, trip=trip,
                                     source=trip_request.source, destination=trip_request.destination)
        trip_request.containing_set.close()

    @staticmethod
    @atomic
    def decline_request(trip, trip_request_id):
        trip_request = get_object_or_404(TripRequest, id=trip_request_id, trip=trip)
        trip_request.status = TripRequest.DECLINED_STATUS
        trip_request.save()


class AutomaticJoinRequestManager(View):
    TRIP_SCORE_THRESHOLD = 0.05

    @staticmethod
    def get(request):
        return render(request, 'automatically_join_trip_form.html', {'form': AutomaticJoinTripForm()})

    @classmethod
    def post(cls, request):
        form = AutomaticJoinTripForm(data=request.POST, user=request.user,
                                     trip_score_threshold=cls.TRIP_SCORE_THRESHOLD)

        if form.is_valid():
            trip = form.join_a_trip_automatically()
            if trip is not None:
                return redirect(reverse('trip:trip', kwargs={'trip_id': trip.id}))
            return render(request, 'trip_not_found.html')

        return HttpResponseBadRequest()


@login_required
@only_get_allowed
def get_trip_page_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    if Trip.get_accessible_trips_for(request.user).filter(id=trip_id).exists():
        return render(request, 'trip_page.html', {
            'trip': trip,
        })
    else:
        return HttpResponseForbidden()


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
                vote = Vote.objects.get(sender=request.user, receiver=members[i])
                rate.append(vote.rate)
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
        vote = Vote(sender=request.user, receiver=Member.objects.get(id=receiver), rate=rate, trip_id=trip_id)
        vote.save()
        members = []
        rate = []
        trip = Trip.objects.get(id=trip_id)
        members.extend(trip.passengers.all())
        members.append(trip.car_provider)
        members.remove(request.user)
        for i in range(len(members)):
            try:
                vote = Vote.objects.get(sender=request.user, receiver=members[i])
                rate.append(vote.rate)
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


class SearchTripsManager(View):
    @classmethod
    def get(cls, request):
        if cls.is_valid_search_parameter(request.GET):
            return cls.do_search(request) if request.GET else render(request, "search_trip.html")
        return HttpResponseBadRequest()

    @classmethod
    def do_search(cls, request):
        data = request.GET
        source = extract_source(data)
        destination = extract_destination(data)
        trips = (request.user.driving_trips.all() | request.user.partaking_trips.all()).distinct().exclude(
            status=Trip.DONE_STATUS)
        if data['start_time'] != "-1":
            trips = cls.filter_by_dates(data['start_time'], data['end_time'], trips)
        trips = sorted(trips, key=lambda trip: (
            get_trip_score(trip, source=source, destination=destination)))
        trips = filter(lambda trip: get_trip_score(trip, source, destination) != np.inf, trips)
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


@login_required
@only_get_allowed
def get_playlist_view(request, trip_id):
    playlist_id = Trip.objects.get(id=trip_id).playlist_id
    return render(request, 'music_player.html', {"playlist_id": playlist_id, 'trip_id': trip_id})


class QuickMessageTripManager(View):
    @method_decorator(login_required)
    def get(self, request, trip_id, user_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user.id == user_id and trip.status != Trip.IN_ROUTE_STATUS:
            return HttpResponseBadRequest()
        if trip.car_provider == request.user and Companionship.objects.filter(trip_id=trip_id,
                                                                              member_id=user_id).exists():
            return render(request, "trip_quick_message.html", {"messages": CAR_PROVIDER_QUICK_MESSAGES})
        elif Companionship.objects.filter(trip_id=trip_id,
                                          member_id=request.user.id).exists() and trip.car_provider_id == user_id:
            return render(request, "trip_quick_message.html", {"messages": PASSENGER_QUICK_MESSAGES})
        return HttpResponseForbidden()

    @method_decorator(login_required)
    def post(self, request, trip_id, user_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user.id == user_id and trip.status != Trip.IN_ROUTE_STATUS:
            return HttpResponseBadRequest()
        if trip.car_provider == request.user and Companionship.objects.filter(trip_id=trip_id,
                                                                              member_id=user_id).exists():
            if QuickMessageTripManager.create_mail(request.user, request.POST, user_id):
                return redirect(reverse('trip:trip', kwargs={'trip_id': trip_id}))
            else:
                return HttpResponseBadRequest()
        elif Companionship.objects.filter(trip_id=trip_id,
                                          member_id=request.user.id).exists() and trip.car_provider_id == user_id:
            if QuickMessageTripManager.create_mail(request.user, request.POST, user_id):
                return redirect(reverse('trip:trip', kwargs={'trip_id': trip_id}))
            else:
                return HttpResponseBadRequest()
        return HttpResponseForbidden()

    @staticmethod
    def create_mail(sender, post_data, receiver_id):
        mail_form = QuickMailForm(data=post_data)
        print(post_data.get("message"))
        if mail_form.is_valid():
            mail_obj = mail_form.save(commit=False)
            mail_obj.sender = sender
            mail_obj.receiver = Member.objects.get(id=receiver_id)
            mail_obj.sent_time = timezone.now()
            mail_obj.is_mail_seen = False
            mail_obj.save()
            return True
        return False

