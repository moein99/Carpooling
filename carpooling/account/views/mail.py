from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic.base import View

from account.forms import MailForm
from account.models import Member, Mail
from root.decorators import only_get_allowed


class MailManager(View):
    @staticmethod
    def get(request):
        Mail.objects.filter(is_mail_seen=False, receiver=request.user).update(is_mail_seen=True)
        user_mails = request.user.inbox.all().order_by('-sent_time')
        return render(request, 'inbox.html', {'mails': user_mails, 'mail_form': MailForm()})

    @classmethod
    def post(cls, request):
        mail = cls.create_mail(request.user, request.POST)
        if mail is not None:
            return redirect(reverse('account:user_inbox'))
        return HttpResponseBadRequest("Invalid mail")

    @staticmethod
    def create_mail(sender, post_data):
        mail_form = MailForm(data=post_data)
        if mail_form.is_valid() and Member.objects.filter(username=post_data['to']).exists():
            mail = mail_form.save(commit=False)
            mail.sender = sender
            mail.receiver = Member.objects.get(username=post_data['to'])
            mail.sent_time = timezone.now()
            mail.is_mail_seen = False
            mail.save()
            return mail
        return None


@login_required
@only_get_allowed
def get_sent_mails(request):
    mails = Mail.objects.filter(sender=request.user).order_by('-sent_time')
    return render(request, "sent_messages.html", {
        "mails": mails
    })
