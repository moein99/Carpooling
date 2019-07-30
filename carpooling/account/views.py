import uuid

import redis
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse

from account.forms import ForgotPasswordForm, ResetPasswordForm
from account.models import Member


class PasswordHandler:
    @staticmethod
    def handle(request):
        certificate = request.GET.get('certificate')
        if request.method == 'GET':
            if certificate is None:
                return render(request, 'forgot_password.html', {'form': ForgotPasswordForm()})
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
        return render(request, 'reset_password.html', {'form': ResetPasswordForm(initial={'certificate': certificate})})

    @staticmethod
    def create_email_text(user, certificate):
        email_text = render_to_string('reset_password_email.html', {
            'link': 'localhost:8000/account/password/?certificate=' + certificate,
            'user': user,
        })
        return email_text

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
            if form.is_valid():
                email_or_username = form.clean().get('email_or_username')
            user = Member.objects.get(Q(username=email_or_username) | Q(email=email_or_username))
        except Member.DoesNotExist:
            return HttpResponseNotFound()
        certificate = uuid.uuid4().hex
        redis.Redis().set(certificate, user.username, 60 * 15)
        email_text = PasswordHandler.create_email_text(user, certificate)
        PasswordHandler.send_email(user.email, email_text)
        # TODO: create html file
        return HttpResponse("We have sent you a reset password link; Check your email.")

    @staticmethod
    def handle_reset_password(request):
        form = ResetPasswordForm(data=request.POST)
        if form.is_valid():
            certificate = form.clean().get('certificate')
        username = redis.Redis().get(certificate).decode()
        if username is None:
            return HttpResponseForbidden()
        user = Member.objects.get(username=username)
        if form.is_valid():
            user.set_password(form.clean().get('password'))
            return redirect(reverse('account:login'))
        else:
            return HttpResponseBadRequest()
