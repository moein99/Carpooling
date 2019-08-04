from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

import uuid
import redis

from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import logout as logout_user, authenticate
from django.contrib.auth import login as login_user

from account.forms import ForgotPasswordForm, ResetPasswordForm, LoginForm, SignupForm
from account.models import Member


def login(request):
    if request.method == 'POST':
        return handle_login(request)
    elif request.method == 'GET':
        return render(request, 'login.html', {"form": LoginForm()})


def signup(request):
    if request.method == 'GET':
        return render(request, 'signup.html', {'form': SignupForm()})
    elif request.method == 'POST':
        return handle_signup(request)


class LoginHandler:
    def login(self):
        pass

    def handle(self):
        pass


def is_user_exists(username):
    return Member.objects.all().filter(username=username).exists()


def handle_login(request_obj):
    username, password = request_obj.POST.get('username'), request_obj.POST.get('password')
    user = authenticate(username=username, password=password)
    if user and user.is_active:
        login_user(request_obj, user)
        return redirect(reverse('root:home'))
    messages.add_message(request_obj, messages.INFO, 'invalid username or password')
    return render(request_obj, 'login.html', {'form': LoginForm()}, status=403)


def handle_signup(request_obj):
    form = SignupForm(data=request_obj.POST)
    if is_user_exists(form.data['username']):
        messages.add_message(request_obj, messages.INFO, 'this username already exists')
        return render(request_obj, 'signup.html', {'form': SignupForm()})
    if form.is_valid():
        member = form.save(commit=False)
        member.set_password(form.data['password'])
        member.save()
        return redirect(reverse('account:login'))
    return render(request_obj, 'signup.html', {'form': form}, status=400)


@login_required
@csrf_exempt
def logout(request):
    if request.method == "POST":
        logout_user(request)
        return redirect(reverse('root:home'))
    else:
        return HttpResponseBadRequest("Bad Request")


def profile(request):
    return None


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
        email_text += 'http://localhost:8000/account/password/?certificate=' + reset_pass_certificate + '\n'
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

