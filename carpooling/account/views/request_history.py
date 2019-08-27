from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.db.transaction import atomic
from django.http import HttpResponseNotAllowed, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic.base import View

from root.decorators import check_request_type, only_get_allowed
from trip.models import TripRequest, TripRequestSet


class RequestHistoryManager(View):
    @staticmethod
    def get(request):
        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user).annotate(
            last_request=Max("requests__creation_time")).order_by("-last_request")
        return render(request, "request_history.html", {
            "trip_request_sets": trip_request_sets,
        })

    @check_request_type
    def post(self, request):
        return HttpResponseNotAllowed()

    @classmethod
    def put(cls, request):
        target = request.POST.get("target")
        if target == "set":
            cls.close_request_set(request.POST.get("id"))
        elif target == "request":
            if not cls.cancel_request(request.POST.get("id")):
                return HttpResponse("Bad Request", status=400)

        trip_request_sets = TripRequestSet.objects.filter(applicant=request.user).annotate(
            last_request=Max("requests__creation_time")).order_by("-last_request")
        return render(request, "request_history.html", {
            "trip_request_sets": trip_request_sets,
        })

    @staticmethod
    @atomic
    def close_request_set(request_set_id):
        request_set = get_object_or_404(TripRequestSet, id=request_set_id)
        request_set.close()

    @staticmethod
    def cancel_request(request_id):
        request = get_object_or_404(TripRequest, id=request_id)
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
