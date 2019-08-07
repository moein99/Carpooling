from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from account.forms import *
from account.models import Member


class UserProfileHandler:
    ANONYMOUS_PROFILE_STATUS = "ANONYMOUS_PROFILE"
    MEMBER_PROFILE_STATUS = "MEMBER_PROFILE"
    OWNED_PROFILE_STATUS = "OWNED_PROFILE"

    @staticmethod
    def handle_profile(request, user_id):
        if request.method == 'GET':
            return UserProfileHandler.do_get_profile(request, user_id)
        else:
            return HttpResponseNotAllowed("Method Not Allowed")

    @staticmethod
    def do_get_profile(request, user_id):
        if request.user.is_authenticated:
            return UserProfileHandler.show_profile_to_member(request, user_id)
        else:
            return UserProfileHandler.show_profile_to_anonymous(request, user_id)

    @staticmethod
    @login_required
    def show_profile_to_member(request, user_id):
        if request.user.id == user_id:
            return UserProfileHandler.show_my_profile(request)
        else:
            return UserProfileHandler.show_member_profile(request, user_id)

    @staticmethod
    def show_profile_to_anonymous(request, user_id):
        user_data = Member.objects.get(id=user_id)
        return render(request, "profile.html",
                      {"status": UserProfileHandler.ANONYMOUS_PROFILE_STATUS, "member": user_data})

    @staticmethod
    def show_my_profile(request):
        return render(request, "profile.html",
                      {"status": UserProfileHandler.OWNED_PROFILE_STATUS, "member": request.user})

    @staticmethod
    def show_member_profile(request, user_id):
        user_data = Member.objects.get(id=user_id)
        reported = UserProfileHandler.is_reported(request, user_id)

        return render(request, "profile.html",
                      {"status": UserProfileHandler.MEMBER_PROFILE_STATUS, "member": user_data, 'reported': reported})

    @staticmethod
    def is_reported(request, user_id):
        report = Report.objects.filter(reported_id=user_id, reporter_id=request.user.id)
        if len(report):
            days = abs((now() - report[0].date).days)
            if days < 10:
                return True
        return False

    @staticmethod
    @login_required
    def handle_edit_profile(request):
        if request.method == "GET":
            return UserProfileHandler.do_get_edit_profile(request)
        elif request.method == "POST":
            if request.POST.get('type') == "PUT":
                return UserProfileHandler.do_put_edit_profile(request)
            else:
                return HttpResponseNotAllowed("Response Not Allowed")

    @staticmethod
    def do_get_edit_profile(request):
        form = EditProfileForm(instance=request.user)
        return render(request, "edit_profile.html", {"form": form})

    @staticmethod
    def do_put_edit_profile(request):
        UserProfileHandler.update_member(request)
        return redirect(reverse('account:user_profile', kwargs={'user_id': request.user.id}))

    # change this when change models .
    @staticmethod
    def update_member(request):
        user = Member.objects.get(id=request.user.id)
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.bio = request.POST.get('bio')
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        user.phone_number = request.POST.get('phone_number')
        user.save()
