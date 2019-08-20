import json

from django.test import TestCase, Client

from django.urls import reverse
from model_mommy import mommy

from account.models import Member
from group.forms import GroupForm
from group.models import Group, Membership


class GroupViewTest(TestCase):
    def setUp(self):
        user = mommy.make(Member, username='test_user')
        user.set_password('1234')
        user.save()

    def test_unauthorized_get_request(self):
        response = self.client.get(path=reverse('group:groups_list'))
        self.assertEqual(response.status_code, 302)

    def test_unauthorized_post_request(self):
        response = self.client.post(path=reverse('group:create_group'))
        self.assertEqual(response.status_code, 302)

    def test_authorized_get_request(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.get(path=reverse('group:groups_list'))
        self.assertEqual(response.status_code, 200)

    def test_authorized_get_create_request(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.get(path=reverse('group:create_group'))
        self.assertEqual(response.status_code, 200)

    def test_authorized_post_full_fields(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.post(path=reverse('group:create_group'), data={
            'code': "test_group", 'title': "test group title",
            'is_private': True,
            'description': "this is a test group",
            'source_lat': 21.2, 'source_lon': 22.3
        })
        test_group = Group.objects.get(code="test_group")
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(test_group)

    def test_authorized_post_with_empty_fields(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.post(path=reverse('group:create_group'), data={
            'code': "test_group",
            'title': "test group title",
            'is_private': True,
            'description': "this is a test group",
        })
        self.assertEqual(response.status_code, 302)
        test_group = Group.objects.get(code="test_group")
        self.assertIsNotNone(test_group)

    def test_adding_user_to_group(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.post(path=reverse('group:create_group'), data={
            'code': "test_group",
            'title': "test group title", 'is_private': True,
            'description': "this is a test group",
        })
        test_group = Group.objects.get(code="test_group")
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(test_group)
        test_membership = Membership.objects.get(group__exact=test_group)
        self.assertIsNotNone(test_membership)

    def test_public_group_get_request(self):
        self.client.login(username='test_user', password='1234')
        response = self.client.get(path=reverse('group:create_group'), data={'type': 'leave'})
        self.assertEqual(response.status_code, 200)

    def test_group_members(self):
        self.client.login(username='test_user', password='1234')
        group = mommy.make(Group, is_private=False)
        response = self.client.get(path=reverse('group:group_members', kwargs={'group_id': group.id}))
        self.assertEqual(response.status_code, 200)

    def test_get_group_members_as_owner(self):
        self.client.login(username='test_user', password='1234')
        user = Member.objects.get(username='test_user')
        group = mommy.make(Group, is_private=True)
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='ow')
        response = self.client.get(path=reverse('group:group_members', kwargs={'group_id': group.id}))
        self.assertEqual(response.status_code, 200)

    def test_private_unauthorized_get_members(self):
        self.client.login(username='test_user', password='1234')
        group = mommy.make(Group, is_private=True)
        response = self.client.get(path=reverse('group:group_members', kwargs={'group_id': group.id}))
        self.assertEqual(response.status_code, 403)


class GroupFormTest(TestCase):

    def test_wrong_group_form(self):
        w = mommy.make(Group)
        data = {'code': w.code, 'title': w.title, 'description': w.description}
        form = GroupForm(data=data)
        self.assertFalse(form.is_valid())

    def test_correct_group_form(self):
        data = {'code': "test_group", 'title': "test group title", 'is_private': True,
                'description': "this is a test group"}
        form = GroupForm(data=data)
        self.assertTrue(form.is_valid())


class AddMemberToGroupTest(TestCase):
    def setUp(self):
        user = Member.objects.create(username="test_user")
        user.set_password('1234')
        user.save()

    def test_add_user_to_group(self):
        self.client.login(username='test_user', password='1234')
        group = mommy.make(Group)
        response = self.client.post(path=reverse('group:group', kwargs={'group_id': group.id}), data={'action': 'join'})
        test_membership = Membership.objects.get(group_id=group.id, member__username='test_user')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(test_membership)

    def test_user_leave_from_group(self):
        self.client.login(username='test_user', password='1234')
        user = Member.objects.get(username='test_user')
        group = mommy.make(Group, is_private=False)
        mommy.make(Membership, group=group, member=user)
        response = self.client.post(path=reverse('group:group', kwargs={'group_id': group.id}),
                                    data={'action': 'leave'})
        test_membership = Membership.objects.filter(group_id=group.id, member__username='test_user')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(test_membership))

    def test_owner_add_other_members(self):
        member, group = self.get_objects(True)
        user = Member.objects.get(username='test_user')
        mommy.make(Membership, member_id=user.id, group_id=group.id, role='ow')
        response = self.client.post(path=reverse('group:group', kwargs={'group_id': group.id}),
                                    data={'action': 'add', 'username': member.username})
        test_membership = Membership.objects.get(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(test_membership)

    def test_private_unauthorized_group_access(self):
        self.client.login(username='test_user', password='1234')
        group = mommy.make(Group, is_private=True)
        response = self.client.post(path=reverse('group:group', kwargs={'group_id': group.id}), data={'action': 'join'})
        test_membership = Membership.objects.filter(group_id=group.id, member__username='test_user')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(0, len(test_membership))

    def test_add_not_created_member(self):
        self.client.login(username='test_user', password='1234')
        user = Member.objects.get(username='test_user')
        group = mommy.make(Group)
        mommy.make(Membership, member_id=user.id, group_id=group.id, role='ow')
        response = self.client.post(path=reverse('group:group', kwargs={'group_id': group.id}),
                                    data={'action': 'add', 'username': "undefined"})
        self.assertEqual(response.status_code, 404)

    def test_delete_member_as_owner(self):
        member, group = self.get_objects(False)
        user = Member.objects.get(username='test_user')
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='ow')
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me')
        response = self.client.post(reverse('group:group_members', kwargs={'group_id': group.id}), data={
            'type': 'DELETE',
            'member_id': member.id,
        })
        test_membership = Membership.objects.filter(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(0, len(test_membership))

    def test_unauthorized_delete_member(self):
        member, group = self.get_objects(True)
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me', )
        response = self.client.post(reverse('group:group_members', kwargs={'group_id': group.id}), data={
            'type': 'DELETE',
            'member_id': member.id,
        })
        test_membership = Membership.objects.get(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(test_membership)

    def test_delete_member_as_member(self):
        member, group = self.get_objects(True)
        user = Member.objects.get(username='test_user')
        mommy.make(Membership, group_id=group.id, member_id=user.id, role='me')
        mommy.make(Membership, group_id=group.id, member_id=member.id, role='me')
        response = self.client.post(reverse('group:group_members', kwargs={'group_id': group.id}), data={
            'type': 'DELETE',
            'member_id': member.id,
        })
        test_membership = Membership.objects.filter(group_id=group.id, member_id=member.id)
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(test_membership)

    def get_objects(self, is_private):
        self.client.login(username='test_user', password='1234')
        group = mommy.make(Group, is_private=is_private)
        member = mommy.make(Member, _fill_optional=['email'])
        return member, group


class SearchGroupsTest(TestCase):
    def setUp(self):
        Member.objects.create_user(username='test_user', password='1234')
        self.client = Client()
        self.client.login(username="test_user", password="1234")

    def test_search_groups(self):
        mommy.make(Group, title='bazaar')
        mommy.make(Group, title='cafebazaar')
        mommy.make(Group, title='divar')
        response = self.client.get(reverse('group:group_search', kwargs={'query': 'bazaar'}))
        response_in_json = json.loads(response.content)
        result_groups_titles = [group['title'] for group in response_in_json['groups']]
        self.assertTrue('bazaar' in result_groups_titles and
                        'cafebazaar' in result_groups_titles and
                        'divar' not in result_groups_titles)
