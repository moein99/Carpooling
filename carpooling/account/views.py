import uuid

from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
import redis

from django.urls import reverse
from django.core.mail import send_mail


from account.forms import ForgotPasswordForm, ResetPasswordForm
from account.models import Member


class PasswordHandler:
    @staticmethod
    def handle(request):
        certificate = request.GET.get('certificate')
        if request.method == 'GET':
            if certificate is None:
                render(request, 'forgot_password.html', {'form': ForgotPasswordForm()})
            else:
                return PasswordHandler.render_reset_password(request)
        elif request.method == 'POST':
            type = request.POST.get('type')
            if type is None:
                return HttpResponseBadRequest()
            if type == 'POST':
                return PasswordHandler.email_reset_password_link(request)
            elif type == 'PUT':
                return PasswordHandler.handle_reset_password(request)

    @staticmethod
    def render_reset_password(request):
        certificate = request.GET.get('certificate')
        r = redis.Redis()
        username = r.get(certificate)
        if username is None:
            return HttpResponseNotFound()
        render(request, 'reset_password.html', {'form': ResetPasswordForm(certificate)})

    @staticmethod
    def create_email_text(user, certificate):
        return certificate

    @staticmethod
    def send_email(email_address, email_text):
        send_mail(
            'Reset Password',
            email_text,
            'carpooling.cafebazaar@gmail.com',
            [email_address],
            fail_silently=False,
        )

    @staticmethod
    def email_reset_password_link(request):
        form = ForgotPasswordForm(data=request.POST)
        try:
            user = Member.objects.get(Q(username=form.email_or_username) | Q(email=form.email_or_username))
        except Member.DoesNotExist():
            return HttpResponseNotFound()
        certificate = uuid.uuid4().hex
        redis.Redis().set(certificate, user.username, 60*15)
        email_text = PasswordHandler.create_email_text(user, certificate)
        PasswordHandler.send_email(user.email, email_text)
        # TODO: create html file
        return HttpResponse("We have sent you a reset password link; Check your email.")

    @staticmethod
    def handle_reset_password(request):
        form = ResetPasswordForm(data=request.POST)
        certificate = form.certificate
        username = redis.Redis().get(certificate)
        if username is None:
            return HttpResponseForbidden()
        user = Member.objects.get(username=username)
        if form.is_valid():
            user.set_password(form.password)
            return redirect(reverse('account:login'))
        else:
            return HttpResponseBadRequest()