from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import generic
from django.views.generic.base import View

from account.forms import *
from account.models import Member
from trip.models import Vote


class SignUp(generic.CreateView):
    form_class = SignupForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'


class UserProfileManager(View):
    ANONYMOUS_PROFILE_STATUS = "ANONYMOUS_PROFILE"
    MEMBER_PROFILE_STATUS = "MEMBER_PROFILE"
    OWNED_PROFILE_STATUS = "OWNED_PROFILE"

    def get(self, request, user_id):
        edit = (request.GET.get('edit', 'false') == 'true')
        if edit:
            return self.get_edit_profile(request, user_id)
        else:
            return self.get_profile(request, user_id)

    @staticmethod
    @login_required
    def get_edit_profile(request, user_id):
        if user_id != request.user.id:
            return HttpResponseForbidden()
        form = EditProfileForm(instance=request.user)
        return render(request, "edit_profile.html", {"form": form})

    @staticmethod
    def get_profile(request, user_id):
        if request.user.is_authenticated:
            return UserProfileManager.show_profile_to_member(request, user_id)
        else:
            return UserProfileManager.show_profile_to_anonymous(request, user_id)

    @staticmethod
    @login_required
    def show_profile_to_member(request, user_id):
        if request.user.id == user_id:
            return UserProfileManager.show_my_profile(request, user_id)
        else:
            return UserProfileManager.show_member_profile(request, user_id)

    @staticmethod
    def show_profile_to_anonymous(request, user_id):
        user_data = Member.objects.get(id=user_id)
        votes = Vote.objects.filter(receiver=Member.objects.get(id=user_id))
        rate = -1
        if len(votes) != 0:
            rate = votes.aggregate(Sum('rate'))['rate__sum'] // votes.count()
        return render(request, "profile.html",
                      {"status": UserProfileManager.ANONYMOUS_PROFILE_STATUS, "member": user_data,
                       "rate": rate})

    @staticmethod
    def show_my_profile(request, user_id):
        user_comments = UserProfileManager.get_user_comments(user_id)
        votes = Vote.objects.filter(receiver=Member.objects.get(id=user_id))
        rate = -1
        if len(votes) != 0:
            rate = votes.aggregate(Sum('rate'))['rate__sum'] // votes.count()
        return render(request, "profile.html",
                      {"status": UserProfileManager.OWNED_PROFILE_STATUS, "member": request.user, 'comment_form':
                          CommentForm(), 'user_comments': user_comments, "rate": rate})

    @staticmethod
    def show_member_profile(request, user_id):
        user_data = Member.objects.get(id=user_id)
        reported = UserProfileManager.is_reported(request.user.id, user_id)
        user_comments = UserProfileManager.get_user_comments(user_id)
        votes = Vote.objects.filter(receiver=Member.objects.get(id=user_id))
        rate = -1
        if len(votes) != 0:
            rate = votes.aggregate(Sum('rate'))['rate__sum'] // votes.count()
        return render(request, "profile.html",
                      {"status": UserProfileManager.MEMBER_PROFILE_STATUS, "member": user_data, 'reported': reported,
                       'comment_form': CommentForm(), 'user_comments': user_comments, "rate": rate})

    @staticmethod
    def get_user_comments(prof_id):
        return Comment.objects.filter(receiver_id=prof_id).order_by('-sent_time')

    @staticmethod
    def is_reported(reporter_id, reported_id):
        try:
            return abs((now() - Report.objects.get(reporter_id=reporter_id, reported_id=reported_id).date).days) < 10
        except Report.DoesNotExist:
            return False

    @method_decorator(login_required)
    def post(self, request, user_id):
        type = request.POST.get('type', 'POST')
        if type == 'PUT':
            return self.put(request, user_id)
        if UserProfileManager.create_comment(request.user, Member.objects.get(id=user_id), request.POST):
            return redirect(reverse("account:user_profile", kwargs={'user_id': user_id}))
        return HttpResponseBadRequest("Invalid request")

    @staticmethod
    def create_comment(sender, receiver, post_data):
        comment_form = CommentForm(data=post_data)
        if comment_form.is_valid():
            comment_obj = comment_form.save(commit=False)
            comment_obj.sender = sender
            comment_obj.receiver = receiver
            comment_obj.sent_time = timezone.now()
            comment_obj.save()
            return True
        return False

    @method_decorator(login_required)
    def put(self, request, user_id):
        if user_id != request.user.id:
            return HttpResponseForbidden()
        user = Member.objects.get(id=request.user.id)
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.bio = request.POST.get('bio')
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        user.phone_number = request.POST.get('phone_number')
        user.save()
        return redirect(reverse('account:user_profile', kwargs={'user_id': request.user.id}))

