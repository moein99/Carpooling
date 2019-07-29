from django.test import TestCase
from django.test import Client

# Create your tests here.
from django.urls import reverse

from account.models import Member


class LoginTest(TestCase):
    def setUp(self):
        self.member = Member(username='moein', password='1234')
        self.user = Member.objects.create_user(username=self.member.username, password=self.member.password)
        self.client = Client()

    def test_login(self):
        post_data = {'username': self.member.username, 'password': self.member.password}
        response = self.client.post(reverse('account:login'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_password(self):
        post_data = {'username': self.member.username, 'password': '12345'}
        response = self.client.post(reverse('account:login'), post_data)
        self.assertEqual(response.status_code, 403)

    def test_invalid_username(self):
        post_data = {'username': 'some_one_imaginary', 'password': '12345'}
        response = self.client.post(reverse('account:login'), post_data)
        self.assertEqual(response.status_code, 403)


class SignUpTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signup(self):
        post_data = {"username": "moein", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '1234'}
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

    def test_differ_pass_and_confpass(self):
        post_data = {"username": "moein99", "password": "1234", 'email': "somemail@gmail.com", 'confirm_password': '12'}
        response = self.client.post(reverse('account:signup'), post_data)
        self.assertEqual(response.status_code, 400)