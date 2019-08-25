from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic.base import View

from account.forms import ReportForm


class ReportManager(View):
    @staticmethod
    def get(request, member_id):
        if member_id == request.user.id:
            return HttpResponseForbidden("You can not report your self")
        return render(request, "report.html", {"form": ReportForm()})

    @classmethod
    def post(cls, request, member_id):
        if member_id == request.user.id:
            return HttpResponseForbidden("You can not report your self")
        report = cls.create_report(request.user.id, member_id, request.POST)
        if report is not None:
            return redirect(reverse('account:user_profile', kwargs={'user_id': member_id}))
        return render(request, "report.html", {"form": ReportForm()})

    @staticmethod
    def create_report(reporter_id, reported_id, post_data):
        form = ReportForm(data=post_data)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter_id = reporter_id
            report.reported_id = reported_id
            report.save()
            return report
        return None
