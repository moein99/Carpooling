from django.urls import reverse
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from account.forms import MailForm
from account.models import Member, Mail
from account.views.utils import user_exists


class InboxHandler:

    @staticmethod
    @login_required
    def handle_inbox(request):
        if request.method == "GET":
            Mail.objects.filter(is_mail_seen=False, receiver=request.user).update(is_mail_seen=True)
            return InboxHandler.do_get_inbox(request)
        elif request.method == "POST":
            return InboxHandler.do_post_inbox(request)

    @staticmethod
    def do_get_inbox(request):
        user_mails = request.user.inbox.all().order_by('-sent_time')
        return render(request, 'inbox.html', {'mails': user_mails, 'mail_form': MailForm()})

    @staticmethod
    def do_post_inbox(request):
        mail_form = MailForm(data=request.POST)
        if mail_form.is_valid() and user_exists(request.POST['to']):
            print(mail_form.errors)
            mail_obj = mail_form.save(commit=False)
            mail_obj.sender = request.user
            mail_obj.receiver = Member.objects.get(username=request.POST['to'])
            mail_obj.sent_time = timezone.now()
            mail_obj.is_mail_seen = False
            mail_obj.save()
            return redirect(reverse('account:user-inbox'))
        return HttpResponseBadRequest("invalid mail")
