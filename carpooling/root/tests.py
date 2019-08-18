from django.test import TestCase, Client
from django.urls import reverse
import json

from account.models import Member
from model_mommy import mommy


class SearchPeopleTest(TestCase):
    def setUp(self):
        mommy.make(Member, username='moein', password='1234', _fill_optional=['email'])
        mommy.make(Member, username='sepehr', password='1234', _fill_optional=['email'])
        mommy.make(Member, username='sajjad', password='1234', _fill_optional=['email'])
        mommy.make(Member, username='sepi', password='1234', _fill_optional=['email'])
        self.client = Client()

    def test_search_members(self):
        self.client.login(username="moein", password="1234")
        response = self.client.get(reverse('root:search_people', kwargs={"query": 'se'}))
        response_in_json = json.loads(response.content)
        result_people_user_names = [person['user_name'] for person in response_in_json['people']]
        self.assertTrue('sepehr' in result_people_user_names and
                        'sepi' in result_people_user_names and
                         not 'sajjad' in result_people_user_names)
