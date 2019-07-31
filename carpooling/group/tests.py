from django.test import TestCase

# Create your tests here.
from model_mommy import mommy

from account.models import Member
from group.forms import GroupForm
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

    def test_authorized_get_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(path='/group/create/')
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

    def test_public_group_get_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(path='/group/public/', data={'type': 'leave'})
        self.assertEqual(response.status_code, 200)

    def test_group_members(self):
        self.client.login(username='testuser', password='majid123')
        group = mommy.make(Group, is_private=False)
        response = self.client.get(path='/group/{}/member/'.format(group.id))
        self.assertEqual(response.status_code, 200)

    def test_get_group_members_as_owner(self):
        self.client.login(username='testuser', password='majid123')
        user = Member.objects.get(username='testuser')
        group = mommy.make(Group, is_private=True)
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='ow')
        response = self.client.get(path='/group/{}/member/'.format(group.id))
        self.assertEqual(response.status_code, 200)

    def test_private_unauthorized_get_members(self):
        self.client.login(username='testuser', password='majid123')
        group = mommy.make(Group, is_private=True)
        response = self.client.get(path='/group/{}/member/'.format(group.id))
        self.assertEqual(response.status_code, 403)


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


class AddMemberToGroupTest(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_add_user_to_group(self):
        self.client.login(username='testuser', password='majid123')
        group = mommy.make(Group)
        response = self.client.post(path='/group/{}/'.format(group.id), data={'type': 'join'})
        test_membership = Membership.objects.get(group_id=group.id, member__username='testuser')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(test_membership)

    def test_user_leave_from_group(self):
        self.client.login(username='testuser', password='majid123')
        user = Member.objects.get(username='testuser')
        group = mommy.make(Group, is_private=False)
        mommy.make(Membership, group=group, member=user)
        response = self.client.post(path='/group/{}/'.format(group.id), data={'type': 'leave'})
        test_membership = Membership.objects.filter(group_id=group.id, member__username='testuser')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(test_membership))

    def test_owner_add_other_members(self):
        member, group = self.get_objects(True)
        user = Member.objects.get(username='testuser')
        membership = mommy.make(Membership, member_id=user.id, group_id=group.id, role='ow')
        response = self.client.post(path='/group/{}/'.format(group.id),
                                    data={'type': 'add', 'username': member.username})
        test_membership = Membership.objects.get(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(test_membership)

    def test_private_unauthorized_group_access(self):
        self.client.login(username='testuser', password='majid123')
        group = mommy.make(Group, is_private=True)
        response = self.client.post(path='/group/{}/'.format(group.id), data={'type': 'join'})
        test_membership = Membership.objects.filter(group_id=group.id, member__username='testuser')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(0, len(test_membership))

    def test_add_not_created_member(self):
        self.client.login(username='testuser', password='majid123')
        user = Member.objects.get(username='testuser')
        group = mommy.make(Group)
        mommy.make(Membership, member_id=user.id, group_id=group.id, role='ow')
        response = self.client.post(path='/group/{}/'.format(group.id),
                                    data={'type': 'add', 'username': "salam"})
        self.assertEqual(response.status_code, 404)

    def test_delete_member_as_owner(self):
        member, group = self.get_objects(False)
        user = Member.objects.get(username='testuser')
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='ow')
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me')
        response = self.client.post(path='/group/{}/member/remove/{}/'.format(group.id, member.id), data={})
        test_membership = Membership.objects.filter(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(0, len(test_membership))

    def test_unauthorized_delete_member(self):
        member, group = self.get_objects(True)
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me')
        response = self.client.post(path='/group/{}/member/remove/{}/'.format(group.id, member.id), data={})
        test_membership = Membership.objects.get(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(test_membership)

    def test_delete_member_as_member(self):
        member, group = self.get_objects(True)
        user = Member.objects.get(username='testuser')
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='me')
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me')
        response = self.client.post(path='/group/{}/member/remove/{}/'.format(group.id, member.id), data={})
        test_membership = Membership.objects.filter(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(test_membership)

    def test_delete_member_get_request(self):
        member, group = self.get_objects(True)
        response = self.client.get(path='/group/{}/member/remove/{}/'.format(group.id, member.id))
        self.assertEqual(response.status_code, 302)

    def get_objects(self, is_private):
        self.client.login(username='testuser', password='majid123')
        group = mommy.make(Group, is_private=is_private)
        member = mommy.make(Member)
        return member, group