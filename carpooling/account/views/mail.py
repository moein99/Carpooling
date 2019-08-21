from django.urls import reverse
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from account.forms import MailForm
from account.models import Member, Mail
from root.decorators import only_get_allowed


class MailManager(View):
    @method_decorator(login_required)
    def get(self, request):
        Mail.objects.filter(is_mail_seen=False, receiver=request.user).update(is_mail_seen=True)
        user_mails = request.user.inbox.all().order_by('-sent_time')
        return render(request, 'inbox.html', {'mails': user_mails, 'mail_form': MailForm()})

    @method_decorator(login_required)
    def post(self, request):
        if MailManager.create_mail(request.user, request.POST):
            return redirect(reverse('account:user_inbox'))
        return HttpResponseBadRequest("Invalid mail")

    @staticmethod
    def create_mail(sender, post_data):
        mail_form = MailForm(data=post_data)
        if mail_form.is_valid() and Member.objects.filter(username=post_data['to']).exists():
            mail_obj = mail_form.save(commit=False)
            mail_obj.sender = sender
            mail_obj.receiver = Member.objects.get(username=post_data['to'])
            mail_obj.sent_time = timezone.now()
            mail_obj.is_mail_seen = False
            mail_obj.save()
            return True
        return False


@login_required
@only_get_allowed
def get_sent_mails(request):
    mails = Mail.objects.filter(sender=request.user)
    return render(request, "sent_messages.html", {
        "mails": mails
    })
