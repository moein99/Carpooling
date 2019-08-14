from django.contrib.gis.geos import Point


def extract_source(post_data):
    return Point(float(post_data['source_lat']), float(post_data['source_lng']))


def extract_destination(post_data):
    return Point(float(post_data['destination_lat']), float(post_data['destination_lng']))