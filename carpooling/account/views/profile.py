from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, HttpResponseNotFound, \
    HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import View

from account.forms import *
from account.models import Member
from root.decorators import check_request_type
from trip.models import Vote


class SignUp(generic.CreateView):
    form_class = SignupForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect(reverse('root:home'))
        return super().dispatch(request, *args, **kwargs)


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
    def get_edit_profile(request, member_id):
        if member_id != request.user.id:
            return HttpResponse('Not Allowed', status=403)
        form = EditProfileForm(instance=request.user)
        return render(request, "edit_profile.html", {"form": form})

    @staticmethod
    def get_profile(request, member_id):
        profile_elements = UserProfileManager.get_user_basic_data(get_object_or_404(Member, id=member_id))
        if request.user.is_authenticated:
            profile_elements = UserProfileManager.add_member_specific_data(profile_elements, request.user, member_id)
        return render(request, 'profile.html', profile_elements)

    @staticmethod
    def get_user_basic_data(user):
        votes = UserProfileManager.get_user_received_votes(user.id)
        rate = -1
        if len(votes) != 0:
            rate = votes.aggregate(Sum('rate'))['rate__sum'] // votes.count()
        return {"status": UserProfileManager.ANONYMOUS_PROFILE_STATUS, "member": user, "rate": rate}

    @staticmethod
    def add_member_specific_data(profile_elements, user, member_id):
        profile_elements['user_comments'] = UserProfileManager.get_user_comments(member_id)
        profile_elements['comment_form'] = CommentForm()
        if user.id == member_id:
            profile_elements['status'] = UserProfileManager.OWNED_PROFILE_STATUS
        else:
            profile_elements['reported'] = UserProfileManager.is_reported(user.id, member_id)
            profile_elements['status'] = UserProfileManager.MEMBER_PROFILE_STATUS
        return profile_elements

    @staticmethod
    def get_user_received_votes(member_id):
        return Vote.objects.all().filter(receiver_id=member_id)

    @staticmethod
    def get_user_sent_votes(member_id):
        return Vote.objects.all().filter(sender_id=member_id)

    @staticmethod
    def get_user_comments(member_id):
        return Comment.objects.filter(receiver_id=member_id).order_by('-sent_time')

    @staticmethod
    def is_reported(reporter_id, reported_id):
        return abs((now() - get_object_or_404(Report, reporter_id=reporter_id, reported_id=reported_id).date).days) < 10

    @method_decorator(login_required)
    @check_request_type
    def post(self, request, user_id):
        if UserProfileManager.create_comment(request.user, Member.objects.get(id=user_id), request.POST):
            return redirect(reverse("account:user_profile", kwargs={'user_id': user_id}))
        return HttpResponse("Invalid request", status=400)

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
            return HttpResponse("Not Allowed", status=403)
        UserProfileManager.update_member_profile(request)
        return redirect(reverse('account:user_profile', kwargs={'user_id': request.user.id}))

    @staticmethod
    def update_member_profile(request):
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.bio = request.POST.get('bio')
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        user.phone_number = request.POST.get('phone_number')
        user.save()
