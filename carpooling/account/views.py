import uuid

from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
import redis

# Create your views here.
from django.urls import reverse

from account.forms import ForgotPasswordForm, ResetPasswordForm
from account.models import Member


def render_reset_password(request):
    certificate = request.GET.get('certificate')
    r = redis.Redis()
    username = r.get(certificate)
    if username is None:
        return HttpResponseNotFound()
    render(request, 'reset_password.html', {'form': ResetPasswordForm(certificate)})


def create_email_text(user, certificate):
    return ""


def send_email(email_address, email_text):
    pass


def email_reset_password_link(request):
    form = ForgotPasswordForm(data=request.POST)
    try:
        user = Member.objects.get(Q(username=form.email_or_username) | Q(email=form.email_or_username))
    except Member.DoesNotExist():
        return HttpResponseNotFound()
    certificate = uuid.uuid4()
    redis.Redis().set(certificate, user.username, 60*15)
    email_text = create_email_text(user, certificate)
    send_email(user.email, email_text)
    # TODO: create html file
    return HttpResponse("We have sent you a reset password link; Check your email.")


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


def password(request):
    certificate = request.GET.get('certificate')
    if request.method == 'GET':
        if certificate is None:
            render(request, 'forgot_password.html', {'form': ForgotPasswordForm()})
        else:
            return render_reset_password(request)
    elif request.method == 'POST':
        type = request.POST.get('type')
        if type is None:
            return HttpResponseBadRequest()
        if type == 'POST':
            return email_reset_password_link(request)
        elif type == 'PUT':
            return handle_reset_password(request)
