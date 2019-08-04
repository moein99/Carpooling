from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse

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

        if group.is_private:
            if request.user.is_anonymous or not request.user.is_authenticated:
                return redirect(reverse('account:login'))
            elif not Membership.objects.filter(member=request.user, group=group).exists():
                return HttpResponseForbidden()
        return render(request, 'show_trips.html', {'trips': group.trip_set.all()})

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
        return render(request, 'show_trips_categorized_by_group.html', {'groups': groups})

    @staticmethod
    @login_required(login_url='/account/login/')
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
        trips = (user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
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
