from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.transaction import atomic
from django.http import HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed

from group.models import Group, Membership
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm, TripRequestForm
from trip.models import Trip, TripGroups, Companionship, TripRequest, TripRequestSet
from expiringdict import ExpiringDict

user_groups_cache = ExpiringDict(max_len=100, max_age_seconds=5*60)

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
    def create_trip(car_provider, post_date):
        source = Point(float(post_date['source_lat']), float(post_date['source_lng']))
        destination = Point(float(post_date['destination_lat']), float(post_date['destination_lng']))
        trip_form = TripForm(data=post_date)
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
        trip = get_object_or_404(Trip, id=trip_id)
        if request.method == 'GET':
            return TripHandler.do_get_trip(request, trip)
        else:
            return HttpResponseNotAllowed(['GET'])

    @staticmethod
    def do_get_trip(request, trip):
        if not trip.is_private or Membership.objects.filter(group__in=trip.groups, member=request.user):
            return render(request, 'trip_info.html', {'trip': trip})
        else:
            return HttpResponseForbidden()

    @staticmethod
    @login_required
    def handle_requests(request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        if request.method == 'GET':
            return TripHandler.do_get_requests(request, trip)
        elif request.method == 'POST':
            type = request.POST.get('type', 'POST')
            if type == 'POST':
                return TripHandler.do_post_requests(request, trip)
            elif type == 'PUT':
                return TripHandler.do_put_requests(request, trip)

    @staticmethod
    def do_get_requests(request, trip):
        if request.user == trip.car_provider:
            return TripHandler.show_trip_requests(request, trip)
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

    @staticmethod
    def do_post_requests(request, trip):
        if request.user == trip.car_provider:
            return HttpResponseForbidden()
        source = TripHandler.extract_source(request.POST)
        destination = TripHandler.extract_destination(request.POST)
        form = TripRequestForm(user=request.user, trip=trip, data=request.POST)
        if form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_request = TripHandler.create_trip_request(form, source ,destination)
            # return something
        else:
            return render(request, 'join_trip.html', {'form': form})

    @staticmethod
    def extract_source(post_data):
        return Point(float(post_data['source_lat']), float(post_data['source_lng']))

    @staticmethod
    def extract_destination(post_data):
        return Point(float(post_data['destination_lat']), float(post_data['destination_lng']))

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
        return trip_request

    @staticmethod
    def do_put_requests(request, trip):
        if request.user != trip.car_provider:
            return HttpResponseForbidden()
        try:
            trip_request_id = int(request.POST.get('request_id'))
        except (ValueError, TypeError):
            return HttpResponseBadRequest()
        return TripHandler.accept_request_if_trip_is_not_full(request, trip, trip_request_id)

    @staticmethod
    @atomic
    def accept_request_if_trip_is_not_full(request, trip, trip_request_id):
        if trip.capacity > Companionship.objects.filter(trip=trip).count():
            trip_request = get_object_or_404(TripRequest, id=trip_request_id)
            trip_request.status = TripRequest.ACCEPTED_STATUS
            trip_request.save()
            trip_request.containing_set.close()
            return TripHandler.show_trip_requests(request, trip)
        else:
            return TripHandler.show_trip_requests(request, trip, "trip is full")

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
