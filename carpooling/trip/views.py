from datetime import datetime

import numpy as np
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseBadRequest, HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView
from django.views.generic.base import View
from expiringdict import ExpiringDict
from geopy.distance import distance as point_distance

from account.models import Member
from carpooling.settings import DISTANCE_THRESHOLD
from group.models import Group, Membership
from root.decorators import check_request_type, only_get_allowed
from trip.forms import AutomaticJoinTripForm
from trip.forms import TripForm, TripRequestForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet, Vote
from trip.utils import extract_source, extract_destination
from trip.utils import get_trip_score
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
        return HttpResponse('Request Not Allowed', status=405)

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
                return HttpResponse('Trip status is not waiting', status=400)
            return cls.show_trip_requests(request, trip)

        elif trip in Trip.get_accessible_trips_for(request.user):
            if trip.status != trip.WAITING_STATUS:
                return HttpResponse('Trip status is not waiting', status=400)
            return cls.show_create_request_form(request)
        else:
            return HttpResponse('You have not access to this trip', status=401)

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
            return HttpResponse('Not Allowed', status=403)

        if trip not in Trip.get_accessible_trips_for(request.user):
            return HttpResponse('You have not access to this trip', status=403)

        if trip.status != trip.WAITING_STATUS:
            return HttpResponse('Trip status is not waiting', status=400)

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

    @classmethod
    def put(cls, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.user != trip.car_provider:
            return HttpResponse('Not Allowed', status=403)

        if trip.status != trip.WAITING_STATUS:
            return HttpResponse('Trip status is not waiting', status=400)

        try:
            trip_request_id = int(request.POST.get('request_id'))
        except (ValueError, TypeError):
            return HttpResponse('Bad Request', status=400)

        # TODO: Handle action field in template
        action = request.POST.get('action', 'accept')
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
            return HttpResponse('Unknown action', status=400)

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
        form = AutomaticJoinTripForm(data=request.POST, user=request.user, trip_score_threshold=cls.TRIP_SCORE_THRESHOLD)

        if form.is_valid():
            trip = form.join_a_trip_automatically()
            if trip is not None:
                return redirect(reverse('trip:trip', kwargs={'pk': trip.id}))
            return render(request, 'trip_not_found.html')

        return HttpResponse('Bad Request', status=400)


class TripDetailView(DetailView):
    model = Trip
    template_name = 'trip_page.html'

    def get_context_data(self, **kwargs):
        context = super(TripDetailView, self).get_context_data(**kwargs)
        context['is_user_in_trip'] = self.is_user_in_trip(self.request.user)
        context['user_request_already_sent'] = self.is_join_request_already_sent()
        if self.object.status == self.object.DONE_STATUS and context['is_user_in_trip']:
            context['votes'] = self.get_votes()
        return context

    @check_request_type
    def post(self, request, pk):
        self.object = self.get_object()
        return self.handle_vote_request()

    def handle_vote_request(self):
        receiver = Member.objects.get(id=int(self.request.POST['receiver_id']))
        rate = self.request.POST['rate']
        if self.is_vote_request_valid(receiver, int(rate)):
            is_vote_created = self.create_vote(receiver, int(rate))
            if is_vote_created:
                return HttpResponse("OK")
        return HttpResponseForbidden("permission denied")

    def is_vote_request_valid(self, receiver, rate):
        return self.is_user_in_trip(self.request.user) and self.object.status == self.object.DONE_STATUS and \
               receiver != self.request.user and 1 <= rate <= 5 and self.is_user_in_trip(receiver)

    def put(self, request, pk):
        self.object = self.get_object()
        action = self.request.POST['action']
        if action == "leave":
            return self.handle_leave_request()

        if action == "update_status":
            return self.handle_updating_trip_request()

        if action == "open_trip":
            return self.handle_opening_trip_request()

    def handle_leave_request(self):
        if self.is_user_in_trip(self.request.user):
            user_id = self.request.POST['user_id']
            self.handle_member_leaving_trip(user_id)
            return HttpResponse(str(reverse('root:home')))
        return HttpResponseBadRequest('User is not in trip')

    def handle_updating_trip_request(self):
        if self.request.user == self.object.car_provider:
            self.update_status()
            return HttpResponse(str(reverse('trip:trip', kwargs={'pk': self.object.id})))
        return HttpResponseForbidden('Permission denied')

    def handle_opening_trip_request(self):
        if self.request.user == self.object.car_provider and self.object.status == self.object.CLOSED_STATUS:
            self.open_trip()
            return HttpResponse(str(reverse('trip:trip', kwargs={'pk': self.object.id})))
        return HttpResponseForbidden('Permission denied')

    def is_user_in_trip(self, user):
        return user in self.object.passengers.all() or user == self.object.car_provider

    def is_join_request_already_sent(self):
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
        if not Vote.objects.filter(sender=self.request.user, receiver=receiver, rate=rate, trip=self.object).exists():
            Vote.objects.create(sender=self.request.user, receiver=receiver, rate=rate, trip=self.object)
            return True
        return False


class TripGroupsManager(View):
    @method_decorator(login_required)
    def get(self, request, trip_id):
        user_nearby_groups = TripGroupsManager.get_nearby_groups(request.user, trip_id)
        return render(request, "trip_add_to_groups.html", {'groups': user_nearby_groups})

    @method_decorator(login_required)
    def post(self, request, trip_id):
        user_nearby_groups = TripGroupsManager.get_nearby_groups(request.user, trip_id)
        trip = get_object_or_404(Trip, id=trip_id)
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


class SearchTripsManager(View):
    @classmethod
    def get(cls, request):
        if cls.is_valid_search_parameter(request.GET):
            return cls.do_search(request) if request.GET else render(request, "search_trip.html")
        return HttpResponse('Request Not Allowed', status=405)

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
