from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import *


def login_handler(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return redirect(reverse('root:home'))
            else:
                messages.add_message(request, messages.INFO, 'invalid username or password')
                return render(request, 'login.html', {'form': LoginForm()}, status=403)
        else:
            messages.add_message(request, messages.INFO, 'invalid username or password')
            return render(request, 'login.html', {'form': LoginForm()}, status=403)
    elif request.method == 'GET':
        return render(request, 'login.html', {"form": LoginForm()})


def signup_handler(request):
    if request.method == 'GET':
        return render(request, 'signup.html', {'form': SignupForm()})
    elif request.method == 'POST':
        form = SignupForm(data=request.POST)
        if is_duplicate_user(form):
            messages.add_message(request, messages.INFO, 'this username already exists')
            return render(request, 'signup.html', {'form': SignupForm()})
        elif form.is_valid():
            member = form.save(commit=False)
            member.set_password(form.data['password'])
            member.save()
            return redirect(reverse('account:login'))
        else:
            return render(request, 'signup.html', {'form': form}, status=400)


def is_duplicate_user(form):
    username = form.data['username']
    return Member.objects.all().filter(username=username).count() != 0
