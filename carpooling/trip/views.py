from django.contrib.auth.decorators import login_required
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm
from trip.models import Trip, TripGroups

DISTANCE_THRESHOLD = 100
# threshold scale: meters

user_groups_cache = {}


class TripManageSystem:

    @staticmethod
    @login_required
    def trip_init(request):
        return render(request, 'trip_manager.html', {'user_trips': request.user.driving_trips.all()})

    @staticmethod
    @login_required
    def trip_creation(request):
        if request.method == 'GET':
            return render(request, 'trip_creation.html', {'form': TripForm()})
        elif request.method == 'POST':
            return TripManageSystem.handle_create(request)

    @staticmethod
    def handle_create(request_obj):
        source = Point(float(request_obj.POST['source_lat']), float(request_obj.POST['source_lng']))
        destination = Point(float(request_obj.POST['destination_lat']), float(request_obj.POST['destination_lng']))

        trip_form = TripForm(data=request_obj.POST)
        if trip_form.is_valid() and TripForm.is_point_valid(source) and TripForm.is_point_valid(destination):
            trip_obj = trip_form.save(commit=False)
            trip_obj.car_provider = request_obj.user
            trip_obj.status = Trip.WAITING_STATUS
            trip_obj.source = source
            trip_obj.destination = destination
            trip_obj.save()
            return redirect(reverse('trip:trip_add_groups', kwargs={'trip_id': trip_obj.id}))
        else:
            return HttpResponseBadRequest('Invalid Request')

    @staticmethod
    @login_required
    def trip_add_groups(request, trip_id):
        user_nearby_groups = TripManageSystem.get_nearby_groups(request.user, trip_id)
        if request.method == 'GET':
            return render(request, "trip_add_group.html", {'groups': user_nearby_groups})
        elif request.method == 'POST':
            TripManageSystem.handle_trip_group_relation(request, trip_id, user_nearby_groups)
            return redirect(reverse("trip:trip_page", kwargs={'trip_id': trip_id}))

    @staticmethod
    def get_nearby_groups(user, trip_id):
        if (user.id, trip_id) in user_groups_cache:
            return user_groups_cache[(user.id, trip_id)]
        else:
            user_groups = user.group_set.all()
            trip = get_object_or_404(Trip, pk=trip_id)
            user_nearby_groups = []
            for group in user_groups:
                if group.source is not None and TripManageSystem.is_in_range(group.source, trip.source) or \
                        TripManageSystem.is_in_range(group.source, trip.destination):
                    user_nearby_groups.append(group)
                else:
                    user_nearby_groups.append(group)
            user_groups_cache[(user.id, trip_id)] = user_nearby_groups
            return user_nearby_groups

    @staticmethod
    def is_in_range(first_point, second_point, threshold=DISTANCE_THRESHOLD):
        return point_distance(first_point, second_point).meters <= threshold

    @staticmethod
    def handle_trip_group_relation(request_obj, trip_id, user_nearby_groups):
        trip = Trip.objects.get(id=trip_id)
        for group in user_nearby_groups:
            if request_obj.POST.get(group.code, "") == 'on':
                TripGroups.objects.create(group=group, trip=trip)

    @staticmethod
    def trip_page(request, trip_id):
        return HttpResponse("This will be trip page!")
