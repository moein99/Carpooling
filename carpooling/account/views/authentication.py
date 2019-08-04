from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as logout_user, authenticate
from django.contrib.auth import login as login_user
from account.forms import  LoginForm, SignupForm
from account.models import Member




class AuthenticationHandler:
    @staticmethod
    def handle_login(request):
        if request.method == 'POST':
            return AuthenticationHandler.login(request)
        elif request.method == 'GET':
            return render(request, 'login.html', {"form": LoginForm()})

    @staticmethod
    def handle_signup(request):
        if request.method == 'GET':
            return render(request, 'signup.html', {'form': SignupForm()})
        elif request.method == 'POST':
            return AuthenticationHandler.signup(request)

    @staticmethod
    def is_user_exists(form):
        username = form.data['username']
        return Member.objects.all().filter(username=username).count() != 0

    @staticmethod
    def login(request_obj):
        username, password = request_obj.POST.get('username'), request_obj.POST.get('password')
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            login_user(request_obj, user)
            return redirect(reverse('root:home'))
        messages.add_message(request_obj, messages.INFO, 'invalid username or password')
        return render(request_obj, 'login.html', {'form': LoginForm()}, status=403)

    @staticmethod
    def signup(request_obj):
        form = SignupForm(data=request_obj.POST)
        if AuthenticationHandler.is_user_exists(form):
            messages.add_message(request_obj, messages.INFO, 'this username already exists')
            return render(request_obj, 'signup.html', {'form': SignupForm()})
        if form.is_valid():
            member = form.save(commit=False)
            member.set_password(form.data['password'])
            member.save()
            return redirect(reverse('account:login'))
        return render(request_obj, 'signup.html', {'form': form}, status=400)

    @staticmethod
    @login_required
    @csrf_exempt
    def handle_logout(request):
        if request.method == "POST":
            logout_user(request)
            return redirect(reverse('root:home'))
        else:
            return HttpResponseBadRequest("Bad Request")

