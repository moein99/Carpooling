from django.test import TestCase, Client
from django.urls import reverse
import json

from account.models import Member
from model_mommy import mommy


class SearchPeopleTest(TestCase):
    def setUp(self):
        SearchPeopleTest.make_user("moein", "1234")
        SearchPeopleTest.make_user("sepehr", "1234")
        SearchPeopleTest.make_user("sajjad", "1234")
        SearchPeopleTest.make_user("sepi", "1234")
        self.client = Client()

    @staticmethod
    def make_user(username, password):
        user = mommy.make(Member, username=username)
        user.set_password(password)
        user.save()

    def test_search_members(self):
        self.client.login(username="moein", password="1234")
        response = self.client.get(reverse('root:search_people', kwargs={"query": 'se'}), {'query': 's'})
        response_in_json = json.loads(response.content)
        result_people_user_names = [person['user_name'] for person in response_in_json['people']]
        self.assertTrue('sepehr' in result_people_user_names and
                        'sepi' in result_people_user_names and
                         not 'sajjad' in result_people_user_names)
