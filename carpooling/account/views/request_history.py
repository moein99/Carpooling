from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from root.decorators import check_request_type, only_get_allowed
from trip.models import TripRequest, TripRequestSet, Trip


class RequestHistoryManager(View):

    @method_decorator(login_required)
    def get(self, request):
        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user).annotate(
            last_request=Max("requests__creation_time")).order_by("-last_request")
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
            if not RequestHistoryManager.cancel_request(request.POST.get("id")):
                return HttpResponse("Bad Request", status=400)

        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user).annotate(
            last_request=Max("requests__creation_time")).order_by("-last_request")
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
        if request.is_pending():
            request.status = TripRequest.CANCELED_STATUS
            request.save()
            return True
        return False


@login_required
@only_get_allowed
def get_trip_history(request):
    return render(request, "trip_history.html", {
        "partaking_trips": request.user.partaking_trips.order_by("-start_estimation"),
        "driving_trip": request.user.driving_trips.order_by("-start_estimation")
    })
