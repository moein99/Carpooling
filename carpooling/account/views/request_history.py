from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from root.decorators import check_request_type, only_get_allowed
from trip.models import TripRequest, TripRequestSet, Trip


class RequestHistoryManager(View):

    @method_decorator(login_required)
    def get(self, request):
        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user)
        return render(request, "request_history.html", {
            "trip_request_sets": trip_request_sets,
        })

    @method_decorator(login_required)
    @check_request_type
    def post(self, request):
        return HttpResponseNotAllowed()

    @method_decorator(login_required)
    def put(self, request):
        target = request.POST.get("target")
        if target == "set":
            RequestHistoryManager.close_request_set(request.POST.get("id"))
        elif target == "request":
            RequestHistoryManager.cancel_request(request.POST.get("id"))

        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user)
        return render(request, "request_history.html", {
            "trip_request_sets": trip_request_sets,
        })

    @staticmethod
    def close_request_set(id):
        request_set = get_object_or_404(TripRequestSet, id=id)
        request_set.close()

    @staticmethod
    def cancel_request(id):
        request = get_object_or_404(TripRequest, id=id)
        request.status = TripRequest.CANCELED_STATUS
        request.save()


@login_required
@only_get_allowed
def get_trip_history(request):
    return render(request, "trip_history.html", {
        "partaking_trips": request.user.partaking_trips.all(),
        "driving_trip": request.user.driving_trips.all()
    })
