from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from root.decorators import check_request_type, only_get_allowed
from trip.models import TripRequest, TripRequestSet, Trip


class DoneTripsManager(View):

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
            DoneTripsManager.close_reqeust_set(request.POST.get("id"))
        elif target == "request":
            DoneTripsManager.close_reqeust(request.POST.get("id"))

        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user)
        return render(request, "request_history.html", {
            "trip_request_sets": trip_request_sets,
        })

    @staticmethod
    def close_reqeust_set(id):
        reqeust_set = get_object_or_404(TripRequestSet, id=id)
        reqeust_set.close()
        reqeust_set.save()

    @staticmethod
    def close_reqeust(id):
        request = get_object_or_404(TripRequest, id=id)
        request.status = TripRequest.CANCELED_STATUS
        request.save()


@login_required
@only_get_allowed
def get_trip_history(request):
    joined_trip_history = Trip.objects.filter(companionship__member=request.user).order_by("start_estimation")
    made_trip_history = Trip.objects.filter(car_provider=request.user).order_by("start_estimation")
    return render(request, "trip_history.html", {
        "joined_trip_history": joined_trip_history,
        "made_trip_history": made_trip_history
    })
