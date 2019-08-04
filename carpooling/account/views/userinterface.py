from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from account.forms import *
from account.models import Member


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
