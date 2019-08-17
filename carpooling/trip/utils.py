import numpy as np
from django.contrib.gis.geos import Point

from numpy.linalg import norm


def extract_source(post_data):
    return Point(float(post_data['source_lat']), float(post_data['source_lng']))


def extract_destination(post_data):
    return Point(float(post_data['destination_lat']), float(post_data['destination_lng']))


def subtract_two_point(point1: Point, point2: Point):
    return Point(point1.x - point2.x, point1.y - point2.y)


def get_trip_score(trip, source: Point, destination: Point):
    source_to_trip_source = subtract_two_point(trip.source, source)
    destination_to_trip_destination = subtract_two_point(trip.destination, destination)
    trip_source_to_destination = subtract_two_point(trip.destination, trip.source)
    if np.dot(trip_source_to_destination, subtract_two_point(destination, source)) < 0:
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
