from django.contrib.gis.geos import Point
from django.db.models import Q
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

# Create your tests here.
from account.models import Member
from group.models import Group, Membership
from trip.models import Trip, TripGroups, Companionship


class SearchTripTest(TestCase):
    def setUp(self):
        self.temp_account = Member.objects.create(username="testuser", first_name="javad")
        self.temp_account.set_password('majid123')
        self.temp_account.save()

    def test_anonymous(self):
        response = self.client.get(path=reverse('trip:search-trip'))
        self.assertEqual(response.status_code, 302)

    def test_search_login(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(reverse('trip:search-trip'))
        self.assertEqual(response.status_code, 200)

    # def test_sort_scoring_function(self):
    #     Trip1 = mummy.make

