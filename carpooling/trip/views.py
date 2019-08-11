import numpy as np
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from numpy.linalg import norm

from group.models import Group, Membership
from django.contrib.gis.geos import Point
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from geopy.distance import distance as point_distance

from trip.forms import TripForm
from trip.models import Trip, TripGroups
from expiringdict import ExpiringDict


class SearchTripsManger(View):
    @staticmethod
    def get(request):
        if SearchTripsManger.is_valid_search_parameter(request.GET):
            if request.GET:
                return SearchTripsManger.do_search(request)
            else:
                return render(request, "search_trip")
        else:
            return HttpResponseBadRequest()

    @staticmethod
    def subtract_two_point(point1: Point, point2: Point):
        return Point(point1.x - point2.x, point1.y - point2.y)

    @staticmethod
    def search_sort(query, source: Point, destination: Point):
        source_to_trip_source = SearchTripsManger.subtract_two_point(query.source, source)
        destination_to_trip_destination = SearchTripsManger.subtract_two_point(query.destination, destination)
        trip_source_to_destination = SearchTripsManger.subtract_two_point(query.destination, query.source)

        if np.dot(trip_source_to_destination, SearchTripsManger.subtract_two_point(destination, source)) < 0:
            return 360 + 360
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
        post_data = request.GET
        source = Point(float(post_data['source_lat']), float(post_data['source_lng']))
        destination = Point(float(post_data['destination_lat']), float(post_data['destination_lng']))
        trips = (request.user.driving_trips.all() | request.user.partaking_trips.all()).distinct().exclude(status=Trip.DONE_STATUS)
        trips = sorted(trips, key=lambda query: (SearchTripsManger.search_sort(query, source=source, destination=destination)))[:5]
        return render(request,
                      "trips_viewer.html",
                      {"trips": trips}
                      )

    @staticmethod
    def is_valid_search_parameter(post_data):
        if post_data:
            return 'source_lat' in post_data and 'source_lng' in post_data and 'destination_lat' in post_data and 'destination_lng' in post_data
        else:
            return True
