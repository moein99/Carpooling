from django.utils import timezone
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest
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
        elif request.method == "POST":
            return UserProfileHandler.do_post_profile(request, user_id)

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
            return UserProfileHandler.show_my_profile(request, user_id)
        else:
            return UserProfileHandler.show_member_profile(request, user_id)

    @staticmethod
    def show_profile_to_anonymous(request, user_id):
        user_data = Member.objects.get(id=user_id)
        return render(request, "profile.html",
                      {"status": UserProfileHandler.ANONYMOUS_PROFILE_STATUS, "member": user_data})

    @staticmethod
    def show_my_profile(request, prof_id):
        user_comments = UserProfileHandler.get_user_comments(prof_id)
        return render(request, "profile.html",
                      {"status": UserProfileHandler.OWNED_PROFILE_STATUS, "member": request.user, 'comment_form':
                          CommentForm(), 'user_comments': user_comments})

    @staticmethod
    def show_member_profile(request, prof_id):
        user_data = Member.objects.get(id=prof_id)
        reported = UserProfileHandler.is_reported(request, prof_id)
        user_comments = UserProfileHandler.get_user_comments(prof_id)
        return render(request, "profile.html",
                      {"status": UserProfileHandler.MEMBER_PROFILE_STATUS, "member": user_data, 'reported': reported,
                       'comment_form': CommentForm(), 'user_comments': user_comments})

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

    @staticmethod
    def do_post_profile(request, prof_id):
        is_comment_created = UserProfileHandler.create_comment(request, prof_id)
        if is_comment_created:
            return redirect(reverse("account:user_profile", kwargs={'user_id': prof_id}))
        return HttpResponseBadRequest("invalid request")

    @staticmethod
    def create_comment(request, prof_id):
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            comment_obj = comment_form.save(commit=False)
            comment_obj.sender = request.user
            comment_obj.receiver = Member.objects.get(id=prof_id)
            comment_obj.sent_time = timezone.now()
            comment_obj.save()
            return True
        return False

    @staticmethod
    def get_user_comments(prof_id):
        return Comment.objects.filter(receiver_id= prof_id).order_by('-sent_time')
