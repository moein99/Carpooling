from io import BytesIO

from django.test import TestCase
from django.test import Client
from model_mommy import mommy
from django.urls import reverse

from account.forms import SignupForm
from account.models import Member, Report, Mail, Comment


class LoginTest(TestCase):
    def setUp(self):
        self.member = Member(username='moein', password='1234')
        self.user = Member.objects.create_user(username=self.member.username, password=self.member.password)
        self.client = Client()

    def test_login(self):
        post_data = {'username': self.member.username, 'password': self.member.password}
        response = self.client.post(reverse('account:login'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_active)

    def test_invalid_password(self):
        post_data = {'username': self.member.username, 'password': '12345'}
        response = self.client.post(reverse('account:login'), post_data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.context['user'].is_active)

    def test_invalid_username(self):
        post_data = {'username': 'some_one_imaginary', 'password': '12345'}
        response = self.client.post(reverse('account:login'), post_data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.context['user'].is_active)


class SignUpTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup(self):
        post_data = {"username": "moein", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '1234',
                     'first_name': "my name", 'last_name': 'mylastname', 'phone_number': '09123456789'}
        response = self.client.post(reverse('account:signup'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_email(self):
        post_data = {"username": "moein", "password": "1234", 'email': "somemailgmail.com", 'confirm_password': '1234'}
        response = self.client.post(reverse('account:signup'), post_data)
        self.assertEqual(response.status_code, 400)

    def test_invalid_username(self):
        post_data = {"username": "mo", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '1234'}
        response = self.client.post(reverse('account:signup'), post_data)
        self.assertEqual(response.status_code, 400)

    def test_different_pass(self):
        post_data = {"username": "moein99", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '12'}
        response = self.client.post(reverse('account:signup'), post_data)
        self.assertEqual(response.status_code, 400)


class LogoutTest(TestCase):
    def setUp(self):
        self.client = Client()
        member = Member(username='moein', password='1234')
        self.user = Member.objects.create_user(username=member.username, password=member.password)

    def test_logout(self):
        post_data = {'username': self.user.username, 'password': self.user.password}
        self.client.post(reverse('account:login'), post_data)
        response = self.client.get(reverse('account:logout'))
        self.assertEqual(response.status_code, 302)


class SignupFormTest(TestCase):

    def test_valid_username(self):
        self.data = {'username': "moein", 'password': "1234", 'email': "some@gmail.com", 'confirm_password': "1234",
                     'first_name': "my name", 'last_name': 'mylastname', 'phone_number': '09123456789'}
        self.form = SignupForm(data=self.data)
        self.assertEqual(self.form.is_valid(), True)

        self.data = {'username': "012345678901234567890123456789",
                     'password': "1234", 'email': "some@gmail.com", 'confirm_password': "1234",
                     'first_name': "my name", 'last_name': 'mylastname', 'phone_number': '09123456789'}
        self.form = SignupForm(data=self.data)
        self.assertEqual(self.form.is_valid(), True)

    def test_invalid_username(self):
        self.data = {'username': "moei", 'password': "1234", 'email': "some@gmail.com", 'confirm_password': "1234"}
        self.form = SignupForm(data=self.data)
        self.assertEqual(self.form.is_valid(), False)

        self.data = {'username': "0123456789012345678901234567890",
                     'password': "1234", 'email': "some@gmail.com", 'confirm_password': "1234"}
        self.form = SignupForm(data=self.data)
        self.assertEqual(self.form.is_valid(), False)

    def test_different_password(self):
        self.data = {'username': "moein", 'password': "1234", 'email': "some@gmail.com", 'confirm_password': "12345"}
        self.form = SignupForm(data=self.data)
        self.assertEqual(self.form.is_valid(), False)


class MemberProfileTest(TestCase):

    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_anonymous(self):
        member = mommy.make(Member)
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 200)

    def test_other_members(self):
        self.client.login(username='testuser', password='majid123')
        member = mommy.make(Member)
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 200)

    def test_my_profile(self):
        self.client.login(username='testuser', password='majid123')
        user = Member.objects.get(username='testuser')
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': user.id}))
        self.assertEqual(response.status_code, 200)

    def test_post_request(self):
        member = mommy.make(Member)
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id': member.id}))
        self.assertEqual(response.status_code, 400)


class EditProfileTest(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser", first_name="javad")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_anonymous(self):
        response = self.client.get(path=reverse('account:edit'))
        self.assertEqual(response.status_code, 302)

    def test_edit_profile_get_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(path=reverse('account:edit'))
        self.assertEqual(response.status_code, 200)

    def test_edit_profile(self):
        img = BytesIO(b'mybinarydata')
        img.name = 'myimage.jpg'
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:edit'),
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner',
                                          'profile_picture': img, 'type': 'PUT'})
        self.assertEqual(response.status_code, 302)
        user = Member.objects.get(username='testuser')
        self.assertEqual('sepehr', user.first_name)

    def test_edit_profile_no_image(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:edit'),
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner',
                                          'profile_picture': '', 'type': 'PUT'})
        self.assertEqual(response.status_code, 302)
        user = Member.objects.get(username='testuser')
        self.assertEqual('sepehr', user.first_name)

    def test_edit_profile_not_put_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:edit'),
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner'})
        self.assertEqual(response.status_code, 405)


class ChangePasswordTest(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser", first_name="javad")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_anonymous(self):
        response = self.client.get(path=reverse('account:change_password'))
        self.assertEqual(response.status_code, 302)

    def test_wrong_change_password(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:change_password'),
                                    data={'old_password': 'wrong password', 'password': 'salam', 'type': 'PUT',
                                          'confirm_password': 'salam', 'username': 'testuser'})
        self.assertEqual(response.status_code, 200)

    def test_change_password(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:change_password'),
                                    data={'old_password': 'majid123', 'password': 'salam', 'type': 'PUT',
                                          'confirm_password': 'salam', 'username': 'testuser'})
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('account:login'), data={'username': 'testuser', 'password': 'salam'},
                                    follow=True)
        self.assertTrue(response.context['user'].is_active)

    def test_change_password_wrong_request_type(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:change_password'),
                                    data={'old_password': 'majid123', 'password': 'salam',
                                          'confirm_password': 'salam', 'username': 'testuser'})
        self.assertEqual(response.status_code, 405)


class ReportTest(TestCase):
    def setUp(self):
        self.temp_acount = Member.objects.create(username="testuser", first_name="javad")
        self.temp_acount.set_password('majid123')
        self.temp_acount.save()

    def test_reporting(self):
        self.client.login(username='testuser', password='majid123')
        member = mommy.make(Member)
        response = self.client.post(path=reverse('account:report_member', kwargs={'user_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 302)
        test_report = Report.objects.filter(reported_id=member.id)
        self.assertEqual(1, len(test_report))

    def test_reporting_anonymus(self):
        member = mommy.make(Member)
        response = self.client.post(path=reverse('account:report_member', kwargs={'user_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 302)

    def test_reporting_self(self):
        self.client.login(username='testuser', password='majid123')
        member = Member.objects.get(username='testuser')
        response = self.client.post(path=reverse('account:report_member', kwargs={'user_id': member.id}),
                                    data={'description': 'he is a bad guy'})
        self.assertEqual(response.status_code, 403)


class InboxTest(TestCase):
    def setUp(self):
        self.client = Client()
        post_data = {"username": "moein", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '1234',
                     'first_name': "my name", 'last_name': 'mylastname', 'phone_number': '09123456789'}
        Utils.signup_user(self.client, post_data)
        post_data['username'] = "moein1"
        Utils.signup_user(self.client, post_data)

    def test_sending_mail(self):
        Utils.login_user(self.client, 'moein', '1234')
        mail_data = {'message': "hi moein1", 'to': 'moein1'}
        self.clien405t.post(reverse('account:user-inbox'), mail_data, follow=True)
        receiver = Member.objects.get(username='moein1')
        mail_text = Mail.objects.filter(receiver=receiver)[0].message
        self.assertEqual(mail_text, "hi moein1")

    def test_sending_mail_without_login(self):
        mail_data = {'message': "hi moein1", 'to': 'moein1'}
        response = self.client.post(reverse('account:user-inbox'), mail_data, follow=True)
        self.assertFalse(response.context['user'].is_active)


class CommentTest(TestCase):
    def setUp(self):
        self.client = Client()
        post_data = {"username": "moein", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '1234',
                     'first_name': "my name", 'last_name': 'mylastname', 'phone_number': '09123456789'}
        Utils.signup_user(self.client, post_data)
        post_data['username'] = "moein1"
        Utils.signup_user(self.client, post_data)

    def test_comment(self):
        Utils.login_user(self.client, 'moein', '1234')
        comment_data = {'message': 'hi moein'}
        receiver = Member.objects.get(username='moein1')
        self.client.post(reverse('account:user_profile', kwargs={'user_id': receiver.id}),
                         comment_data,
                         follow=True)
        self.assertEqual(Comment.objects.filter(receiver_id=receiver.id)[0].message, 'hi moein')


class Utils:
    @staticmethod
    def login_user(client, username, password):
        post_data = {'username': username, 'password': password}
        return client.post(reverse('account:login'), post_data, follow=True)

    @staticmethod
    def signup_user(client, post_data):
        return client.post(reverse('account:signup'), post_data)
