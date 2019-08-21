from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from account.forms import ReportForm


class ReportManager(View):
    @method_decorator(login_required)
    def get(self, request, member_id):
        if member_id == request.user.id:
            return HttpResponse("You can not report your self", status=401)
        return render(request, "report.html", {"form": ReportForm()})

    @method_decorator(login_required)
    def post(self, request, member_id):
        if member_id == request.user.id:
            return HttpResponse("You can not report your self", status=401)
        if ReportManager.create_report(request.user.id, member_id, request.POST):
            return redirect(reverse('account:user_profile', kwargs={'user_id': member_id}))
        return render(request, "report.html", {"form": ReportForm()})

    @staticmethod
    def create_report(reporter_id, reported_id, post_data):
        form = ReportForm(data=post_data)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.reporter_id = reporter_id
            instance.reported_id = reported_id
            instance.save()
            return True
        return False
