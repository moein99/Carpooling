from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import logout as logout_user
from django.contrib.auth import login as login_user
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from .forms import *


class AuthorisationHandler:
    @staticmethod
    def handle_login(request):
        if request.method == 'POST':
            return AuthorisationHandler.login(request)
        elif request.method == 'GET':
            return render(request, 'login.html', {"form": LoginForm()})

    @staticmethod
    def handle_signup(request):
        if request.method == 'GET':
            return render(request, 'signup.html', {'form': SignupForm()})
        elif request.method == 'POST':
            return AuthorisationHandler.signup(request)

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
        if AuthorisationHandler.is_user_exists(form):
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


class UserInterfaceHandler:
    ANONYMOUS_PROFILE_STATUS = "ANONYMOUS_PROFILE"
    MEMBER_PROFILE_STATUS = "MEMBER_PROFILE"
    MY_PROFILE_STATUS = "MY_PROFILE"

    @staticmethod
    def handle_profile(request, user_id):
        if request.method == 'GET':
            if request.user.is_authenticated:
                return UserInterfaceHandler.show_profile_to_member(request, user_id)
            else:
                return UserInterfaceHandler.show_profile_to_anonymous(request, user_id)
        else:
            return HttpResponseNotAllowed("Method Not Allowed")

    @staticmethod
    @login_required
    def show_profile_to_member(request, user_id):
        if request.user.id == user_id:
            return UserInterfaceHandler.show_my_profile(request)
        else:
            return UserInterfaceHandler.show_member_profile(request, user_id)

    @staticmethod
    def show_profile_to_anonymous(request, user_id):
        user_data = Member.objects.get(id=user_id)
        return render(request, "profile.html",
                      {"status": UserInterfaceHandler.ANONYMOUS_PROFILE_STATUS, "member": user_data})

    @staticmethod
    def show_my_profile(request):
        return render(request, "profile.html",
                      {"status": UserInterfaceHandler.MY_PROFILE_STATUS, "member": request.user})

    @staticmethod
    def show_member_profile(request, user_id):
        user_data = Member.objects.get(id=user_id)
        return render(request, "profile.html",
                      {"status": UserInterfaceHandler.MEMBER_PROFILE_STATUS, "member": user_data})

    @staticmethod
    @login_required
    def handle_edit_profile(request):
        if request.method == "GET":
            form = EditProfileForm(instance=request.user)
        elif request.method == "POST":
            if request.POST.get('type') == "PUT":
                UserInterfaceHandler.update_member(request)
                return redirect(reverse('account:user_profile', kwargs={'user_id': request.user.id}))
            else:
                return HttpResponseNotAllowed("Response Not Allowed")
        return render(request, "edit_profile.html", {"form": form})

    # change this when change models .
    @staticmethod
    def update_member(request):
        user = Member.objects.get(id=request.user.id)
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.bio = request.POST.get('bio')
        if 'profile_picture' in request.FILES:
            # fs = FileSystemStorage()
            # name = fs.save(request.FILES['profile_picture'].name, request.FILES['profile_picture'])
            user.profile_picture = request.FILES['profile_picture']
        user.phone_number = request.POST.get('phone_number')
        user.save()


def report(request):
    return None


def password(request):
    return None
