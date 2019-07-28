from django.contrib.auth import authenticate, login
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, render_to_response
from .forms import *


# Create your views here.
from django.urls import reverse


def login_init(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return redirect(reverse('root:home'))
            else:
                return HttpResponseBadRequest("Your account was inactive.")
        else:
            return HttpResponseBadRequest("Invalid login details given")
    elif request.method == 'GET':
        return render(request, 'account/login.html', {"form": LoginForm()})


def signup(request):
    if request.method == 'GET':
        return render(request, 'account/signup.html', {'form': SignupForm()})
    else:
        form = SignupForm(data=request.POST)
        if form.is_valid() and form.data['password'] == form.data['confirm_password']:
            member = form.save(commit=False)
            member.set_password(form.data['password'])
            member.save()
            return render_to_response('root/home.html')
        else:
            return render(request, 'account/signup.html', {'form': form})
