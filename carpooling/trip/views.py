from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.shortcuts import render
from trip.models import Trip
from group.models import Group
# Create your views here.


class TripHandler:
    @staticmethod
    def handle_public_trip(request):
        trips = Trip.objects.filter(Q(is_private=False))
        return render(request, 'show_trips.html', {'trips': trips})

    @staticmethod
    def handle_group_trips(request, group_id):
        if request.method == 'GET':
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return HttpResponseNotFound()

            if not group.is_private:
                return render(request, 'show_trips.html', {'trips': group.trip_set})

            if request.user.is_anonymous or not request.user.is_authenticated():
                return HttpResponseForbidden()

            if group.members.get(username=request.user.username):
                return render(request, 'show_trips.html', {'trips': group.trip_set})