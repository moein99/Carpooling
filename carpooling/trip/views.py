from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render

from group.models import Group, Membership
from trip.models import Trip


# Create your views here.
class TripHandler:
    @staticmethod
    def handle_public_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_public_trips(request)

    @staticmethod
    def do_get_public_trips(request):
        trips = Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))
        return render(request, 'show_trips.html', {'trips': trips})

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

        if group.is_private and (
                request.user.is_anonymous or not request.user.is_authenticated or not Membership.objects.filter(
                member=request.user, group=group).exists()):
            return HttpResponseForbidden()
        else:
            return render(request, 'show_trips.html', {'trips': group.trip_set})

    @staticmethod
    @login_required
    def handle_categorized_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_categorized_trips(request)

    @staticmethod
    def get_trips_dict(groups):
        group_name_to_trips = dict()
        for group in groups:
            group_name_to_trips[group.title] = group.trip_set
        return group_name_to_trips

    @staticmethod
    def get_user_groups(user, include_public_groups=False):
        groups = Membership.objects.filter(member=user).values('group')
        if include_public_groups:
            groups = (groups | Group.objects.filter(is_private=False)).distinct()
        return groups

    @staticmethod
    def do_get_categorized_trips(request):
        user = request.user
        if user.is_anonymous or user.is_authenticated:
            user = None

        groups = TripHandler.get_user_groups(user, request.GET.get('include_public_groups') == 'true')
        group_name_to_trips = TripHandler.get_trips_dict(groups)
        return render(request, 'show_trips_categorized_by_group.html', {'groups': group_name_to_trips})

    @staticmethod
    @login_required
    def handle_owned_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_owned_trips(request)

    @staticmethod
    def do_get_owned_trips(request):
        user = request.user
        trips = user.driving_trips.all()
        return render(request, 'show_trips.html', {'trips': trips})

    @staticmethod
    @login_required
    def handle_active_trips(request):
        if request.method == 'GET':
            return TripHandler.do_get_active_trips(request)

    @staticmethod
    def do_get_active_trips(request):
        user = request.user
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct()
        return render(request, 'show_trips.html', {'trips': trips})

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
        return render(request, 'show_available_trips.html', {'trips': trips})
