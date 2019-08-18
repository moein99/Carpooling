from io import BytesIO

from django.test import Client
from django.test import TestCase
from django.urls import reverse
from model_mommy import mommy

from account.models import Member, Report, Mail, Comment


class MemberProfileTest(TestCase):
    def setUp(self):
        self.temp_acount = mommy.make(Member, username="testuser", _fill_optional=['email'])
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_anonymous(self):
        member = mommy.make(Member, _fill_optional=['email'])
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 200)

    def test_other_members(self):
        self.client.login(username='testuser', password='majid123')
        member = mommy.make(Member, _fill_optional=['email'])
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 200)

    def test_my_profile(self):
        self.client.login(username='testuser', password='majid123')
        user = Member.objects.get(username='testuser')
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': user.id}))
        self.assertEqual(response.status_code, 200)

    def test_post_request(self):
        member = mommy.make(Member, _fill_optional=['email'])
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 302)


class EditProfileTest(TestCase):
    def setUp(self):
        self.temp_acount = mommy.make(Member, id=1, username="testuser", first_name="javad", _fill_optional=['email'])
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_anonymous(self):
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id':1}) + '?edit=true')
        self.assertEqual(response.status_code, 302)

    def test_edit_profile_get_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id':1}) + '?edit=true')
        self.assertEqual(response.status_code, 200)

    def test_edit_profile(self):
        img = BytesIO(b'mybinarydata')
        img.name = 'myimage.jpg'
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id':1}) + '?edit=true',
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner',
                                          'profile_picture': img, 'type': 'PUT'})
        self.assertEqual(response.status_code, 302)
        user = Member.objects.get(username='testuser')
        self.assertEqual('sepehr', user.first_name)

    def test_edit_profile_no_image(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id':1}) + '?edit=true',
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner',
                                          'profile_picture': '', 'type': 'PUT'})
        self.assertEqual(response.status_code, 302)
        user = Member.objects.get(username='testuser')
        self.assertEqual('sepehr', user.first_name)

    def test_edit_profile_not_put_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id': 1}),
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner'})
        self.assertEqual(response.status_code, 400)


class ReportTest(TestCase):
    def setUp(self):
        self.temp_acount = mommy.make(Member, username="testuser", first_name="javad", _fill_optional=['email'])
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_reporting(self):
        self.client.login(username='testuser', password='majid123')
        member = mommy.make(Member, _fill_optional=['email'])
        response = self.client.post(path=reverse('account:report_user', kwargs={'member_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 302)
        test_report = Report.objects.filter(reported_id=member.id)
        self.assertEqual(1, len(test_report))

    def test_reporting_anonymus(self):
        member = mommy.make(Member, _fill_optional=['email'])
        response = self.client.post(path=reverse('account:report_user', kwargs={'member_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 302)

    def test_reporting_self(self):
        self.client.login(username='testuser', password='majid123')
        member = Member.objects.get(username='testuser')
        response = self.client.post(path=reverse('account:report_user', kwargs={'member_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 403)


class InboxTest(TestCase):
    def setUp(self):
        self.client = Client()
        user = mommy.make(Member, username='moein', _fill_optional=['email'])
        user.set_password('1234')
        user.save()
        user = mommy.make(Member, username='moein1', _fill_optional=['email'])
        user.set_password('1234')
        user.save()

    def test_sending_mail(self):
        self.client.login(username='moein', password='1234')
        mail_data = {'message': "hi moein1", 'to': 'moein1'}
        self.client.post(reverse('account:user_inbox'), mail_data, follow=True)
        receiver = Member.objects.get(username='moein1')
        mail_text = Mail.objects.get(receiver_id=receiver.id).message
        self.assertEqual(mail_text, "hi moein1")

    def test_sending_mail_without_login(self):
        mail_data = {'message': "hi moein1", 'to': 'moein1'}
        response = self.client.post(reverse('account:user_inbox'), mail_data, follow=True)
        self.assertFalse(response.context['user'].is_active)


class CommentTest(TestCase):
    def setUp(self):
        self.client = Client()
        user = mommy.make(Member, username='moein', _fill_optional=['email'])
        user.set_password('1234')
        user.save()
        user = mommy.make(Member, username='moein1' , _fill_optional=['email'])
        user.set_password('1234')
        user.save()

    def test_comment(self):
        self.client.login(username='moein', password='1234')
        comment_data = {'message': 'hi moein'}
        receiver = Member.objects.get(username='moein1')
        self.client.post(reverse('account:user_profile', kwargs={'user_id': receiver.id}),
                         comment_data,
                         follow=True)
        self.assertEqual(Comment.objects.get(receiver_id=receiver.id).message, 'hi moein')
