from django.test import TestCase

# Create your tests here.
from model_mommy import mommy

from account.models import Member
from group.models import Group


class GroupTestCase(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_unauthorized_group_creation(self):
        response = self.client.get(path='/group/')
        self.assertEqual(response.status_code, 302)

        response = self.client.post(path='/group/')
        self.assertEqual(response.status_code, 302)

    def test_authorized_group_creation(self):
        self.client.login(username='testuser', password='majid123')

        response = self.client.get(path='/group/')
        self.assertEqual(response.status_code, 200)

        response = self.client.post(path='/group/', data={'code': "testgroup", 'title': "test group title",
                                                          'is_private': True, 'description': "this is a test group",
                                                          'source_lat': 21.2, 'source_lon': 22.3})
        self.assertEqual(response.status_code, 200)
        test_group = Group.objects.filter(code="testgroup", title="test group title", is_private=True,
                                          description="this is a test group", source_lat=21.2, source_lon=22.3)
        self.assertIsNotNone(test_group)

        response = self.client.post(path='/group/', data={'code': "testgroup", 'title': "test group title",
                                                          'is_private': True, 'description': "this is a test group"})
        self.assertEqual(response.status_code, 200)
        test_group = Group.objects.filter(code="testgroup", title="test group title", is_private=True,
                                          description="this is a test group", source_lat=21.2, source_lon=22.3)
        self.assertIsNotNone(test_group)
