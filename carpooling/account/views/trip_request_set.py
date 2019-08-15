from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from account.models import Member


class TripRequestSetHandler:
    @staticmethod
    @login_required
    def handle_request_sets_collection(request):
        if request.method == 'GET':
            return TripRequestSetHandler.do_get_request_sets_collection(request)
        elif request.method == 'POST':
            return TripRequestSetHandler.do_post_request_sets_collection(request)

    @staticmethod
    def do_get_request_sets_collection(request):
        return render(request, "signup.html", {'requests_sets': request.user.trip_request_sets})

    @staticmethod
    def do_post_request_sets_collection(request):
        
        pass

