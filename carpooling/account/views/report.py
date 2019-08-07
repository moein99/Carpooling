
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse

from account.forms import ReportForm


class ReportHandler:
    @staticmethod
    @login_required
    def handle_report(request, user_id):
        if user_id != request.user.id:
            if request.method == "GET":
                return render(request, "report.html", {"form": ReportForm()})
            else:
                return ReportHandler.do_post_report(request, user_id)
        else:
            return HttpResponseForbidden("you can not report your self")

    @staticmethod
    def do_post_report(request, user_id):
        form = ReportForm(data=request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.reporter_id = request.user.id
            instance.reported_id = user_id
            instance.save()
            return redirect(reverse('account:user_profile', kwargs={'user_id': user_id}))
        else:
            return render(request, "report.html", {"form": form})
