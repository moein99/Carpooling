
import uuid
import redis
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse
from account.forms import ForgotPasswordForm, ResetPasswordForm
from account.models import Member


class PasswordHandler:
    @staticmethod
    def handle(request):
        reset_pass_certificate = request.GET.get('certificate')
        if request.method == 'GET':
            return PasswordHandler.do_get(request, reset_pass_certificate)
        elif request.method == 'POST':
            return PasswordHandler.do_post(request)

    @staticmethod
    def do_get(request, reset_pass_certificate):
        if reset_pass_certificate is None:
            return render(request, 'forgot_password.html', {'form': ForgotPasswordForm()})
        else:
            return PasswordHandler.render_reset_password_template(request)

    @staticmethod
    def do_post(request):
        type = request.POST.get('type')
        if type is None:
            return HttpResponseBadRequest()
        if type == 'POST':
            return PasswordHandler.handle_reset_password_email(request)
        elif type == 'PUT':
            return PasswordHandler.handle_reset_password(request)

    @staticmethod
    def render_reset_password_template(request):
        reset_pass_certificate = request.GET.get('certificate')
        r = redis.Redis()
        username = r.get(reset_pass_certificate)
        if username is None:
            return HttpResponseNotFound()
        return render(request, 'reset_password.html', {'form': ResetPasswordForm(initial={'certificate': reset_pass_certificate})})

    @staticmethod
    def create_email_text(user, reset_pass_certificate):
        email_text = 'Hi @' + user.username + '!\n'
        email_text += 'Click on the following link to reset your password:\n'
        email_text += 'http://localhost:8000/account/password/reset/?certificate=' + reset_pass_certificate + '\n'
        email_text += 'Regards'
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
    def handle_reset_password_email(request):
        try:
            user = PasswordHandler.get_user(ForgotPasswordForm(data=request.POST))
        except Member.DoesNotExist:
            return HttpResponseNotFound("Account not found!")
        reset_pass_certificate = uuid.uuid4().hex
        redis.Redis().set(reset_pass_certificate, user.username, 60 * 15)
        email_text = PasswordHandler.create_email_text(user, reset_pass_certificate)
        PasswordHandler.send_email(user.email, email_text)
        # TODO: create html file
        return HttpResponse("We have sent you a reset password link; Check your email.")

    @staticmethod
    def get_user(form):
        if form.is_valid():
            email_or_username = form.clean().get('email_or_username')
        return Member.objects.get(Q(username=email_or_username) | Q(email=email_or_username))

    @staticmethod
    def handle_reset_password(request):
        form = ResetPasswordForm(data=request.POST)
        if form.is_valid():
            reset_pass_certificate = form.clean().get('certificate')
        username = redis.Redis().get(reset_pass_certificate).decode()
        if username is None:
            return HttpResponseForbidden()
        user = Member.objects.get(username=username)
        if form.is_valid():
            user.set_password(form.clean().get('password'))
            user.save()
            return redirect(reverse('account:login'))
        else:
            return HttpResponseBadRequest()

