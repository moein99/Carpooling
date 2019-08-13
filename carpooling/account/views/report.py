from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from account.forms import ReportForm


class ReportManager(View):
    @method_decorator(login_required)
    def get(self, request, user_id):
        if user_id == request.user.id:
            return HttpResponseForbidden("You can not report your self")
        return render(request, "report.html", {"form": ReportForm()})

    @method_decorator(login_required)
    def post(self, request, user_id):
        if user_id == request.user.id:
            return HttpResponseForbidden("You can not report your self")
        if ReportManager.create_report(request.user.id, user_id, request.POST):
            return redirect(reverse('account:user_profile', kwargs={'user_id': user_id}))
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
