from django.test import TestCase

# Create your tests here.
from model_mommy import mommy

from account.models import Member
from group.forms import GroupForm, MembershipForm
from group.models import Group, Membership


class GroupViewTestCase(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_unauthorized_get_request(self):
        response = self.client.get(path='/group/')
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_post_request(self):
        response = self.client.post(path='/group/create/')
        self.assertEqual(response.status_code, 302)

    def test_authorized_get_request(self):
        self.client.login(username='testuser', password='majid123')

        response = self.client.get(path='/group/')
        self.assertEqual(response.status_code, 200)

    def test_authorized_post_full_fields(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path='/group/create/', data={'code': "testgroup", 'title': "test group title",
                                                                       'is_private': True,
                                                                       'description': "this is a test group",
                                                                       'source_lat': 21.2, 'source_lon': 22.3})
        test_group = Group.objects.get(code="testgroup")
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(test_group)

    def test_authorized_post_with_empty_fields(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path='/group/create/',
                                    data={'code': "secondgrouptest", 'title': "test group title", 'is_private': True,
                                          'description': "this is a test group", })
        self.assertEqual(response.status_code, 302)
        test_group = Group.objects.get(code="secondgrouptest")
        self.assertIsNotNone(test_group)

    def test_adding_user_to_group(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path='/group/create/', data={'code': "secondgrouptest",
                                                                       'title': "test group title", 'is_private': True,
                                                                       'description': "this is a test group", })
        test_group = Group.objects.get(code="secondgrouptest")
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(test_group)
        test_membership = Membership.objects.get(group__exact=test_group)
        self.assertIsNotNone(test_membership)


class GroupFormTest(TestCase):

    def test_wrong_group_form(self):
        w = mommy.make(Group)
        data = {'code': w.code, 'title': w.title, 'description': w.description}
        form = GroupForm(data=data)
        self.assertFalse(form.is_valid())

    def test_correct_group_form(self):
        data = {'code': "secondgrouptest", 'title': "test group title", 'is_private': True,
                'description': "this is a test group"}
        form = GroupForm(data=data)
        self.assertTrue(form.is_valid())


class MembershipFormTest(TestCase):

    def test_wrong_membership_form(self):
        w = mommy.make(Membership)
        data = {'member': w.member, 'group': w.group, 'role': w.role}
        form = MembershipForm(data=data)
        self.assertFalse(form.is_valid())

    def test_correct_membership_form(self):
        user = mommy.make(Member)
        group = mommy.make(Group)
        data = {'member': user.id, 'group': group.id, 'role': 'ow'}
        form = MembershipForm(data=data)
        self.assertTrue(form.is_valid())
