from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic.base import View
import json
from search import queries as search_query
from account.models import Mail, Member
from group.models import Group


class HomeManager(View):
    @staticmethod
    def get(request):
        data = {}
        if request.user.is_authenticated:
            unread_mails = Mail.objects.filter(is_mail_seen=False, receiver=request.user).count()
            data['unread_mails'] = unread_mails
        return render(request, 'home.html', data)

    @staticmethod
    def post(request):
        return HttpResponseNotAllowed('Method Not Allowed')


class SearchPeopleManager:
    @staticmethod
    @login_required
    def search_people_view(request, query):
        result = {'people': []}
        for member in search_query.profile_username_name_search(data=query)["hits"]["hits"]:
            result['people'].append(SearchPeopleManager.get_member_json(member["_source"]))
        return HttpResponse(json.dumps(result))

    @staticmethod
    def get_member_json(member):
        return {'first_name': member["first_name"], 'last_name': member["last_name"], 'user_name': member["username"], 'url':
            reverse('account:user_profile', kwargs={'user_id': member["id"]})}
