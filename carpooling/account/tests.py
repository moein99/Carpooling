from io import BytesIO

from django.db.models import Q
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from model_mommy import mommy

from account.models import Member, Report, Mail, Comment
from trip.models import Trip, Companionship, TripRequestSet, TripRequest


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
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': 1}) + '?edit=true')
        self.assertEqual(response.status_code, 302)

    def test_edit_profile_get_request(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(path=reverse('account:user_profile', kwargs={'user_id': 1}) + '?edit=true')
        self.assertEqual(response.status_code, 200)

    def test_edit_profile(self):
        img = BytesIO(b'mybinarydata')
        img.name = 'myimage.jpg'
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id': 1}) + '?edit=true',
                                    data={'first_name': 'sepehr', 'phone_number': '09123456789', 'last_name': 'spaner',
                                          'profile_picture': img, 'type': 'PUT'})
        self.assertEqual(response.status_code, 302)
        user = Member.objects.get(username='testuser')
        self.assertEqual('sepehr', user.first_name)

    def test_edit_profile_no_image(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.post(path=reverse('account:user_profile', kwargs={'user_id': 1}) + '?edit=true',
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
        user = mommy.make(Member, username='moein1', _fill_optional=['email'])
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


class TripHistoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = mommy.make(Member, username='moein')
        self.user.set_password('1234')
        self.user.save()

    def test_get_Trip_History(self):
        self.client.login(username='moein', password='1234')
        mommy.make(Trip, car_provider=self.user)
        test_trip = mommy.make(Trip)
        test_companionship = mommy.make(Companionship, trip=test_trip, member=self.user)
        response = self.client.get(reverse("account:trip_history"))
        self.assertEqual(response.status_code, 200)
        trips = response.context['driving_trip']
        self.assertEqual(list(Trip.objects.filter(car_provider=self.user)), list(trips))
        trips = response.context['partaking_trips']
        self.assertEqual(list(Trip.objects.filter(passengers__companionship=test_companionship)), list(trips))


class TripRequestHistoryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = mommy.make(Member, username='moein')
        self.user.set_password('1234')
        self.user.save()

    def test_get_trip_History(self):
        self.client.login(username='moein', password='1234')
        test_trip = mommy.make(Trip)
        test_request_set = mommy.make(TripRequestSet, applicant=self.user)
        mommy.make(TripRequest, trip=test_trip, containing_set=test_request_set)
        response = self.client.get(reverse("account:request_history"))
        self.assertEqual(response.status_code, 200)
        request_set = response.context['trip_request_sets']
        self.assertEqual(list(TripRequestSet.objects.filter(applicant=self.user)), list(request_set))

    def test_close_request_set(self):
        self.client.login(username='moein', password='1234')
        test_trip = mommy.make(Trip)
        test_request_set = mommy.make(TripRequestSet, applicant=self.user)
        mommy.make(TripRequest, trip=test_trip, containing_set=test_request_set)
        response = self.client.post(reverse("account:request_history"), data={
            'type': 'PUT',
            'target': 'set',
            'id': test_request_set.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TripRequestSet.objects.get(applicant=self.user).closed, True)

    def test_cancel_request(self):
        self.client.login(username='moein', password='1234')
        test_trip = mommy.make(Trip)
        test_request_set = mommy.make(TripRequestSet, applicant=self.user)
        test_request = mommy.make(TripRequest, trip=test_trip, containing_set=test_request_set)
        response = self.client.post(reverse("account:request_history"), data={
            'type': 'PUT',
            'target': 'request',
            'id': test_request.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TripRequest.objects.get(id=test_request.id).is_pending(), False)

    def test_cancel_bad_request(self):
        self.client.login(username='moein', password='1234')
        test_trip = mommy.make(Trip)
        test_request_set = mommy.make(TripRequestSet, applicant=self.user)
        test_request = mommy.make(TripRequest, trip=test_trip, containing_set=test_request_set,
                                  status=TripRequest.ACCEPTED_STATUS)
        response = self.client.post(reverse("account:request_history"), data={
            'type': 'PUT',
            'target': 'request',
            'id': test_request.id
        })
        self.assertEqual(response.status_code, 400)


class TestSentMail(TestCase):
    def setUp(self):
        self.client = Client()
        self.sender = mommy.make(Member, username='moein', _fill_optional=['email'])
        self.sender.set_password('1234')
        self.sender.save()
        self.receiver = mommy.make(Member, username='moein2', _fill_optional=['email'])
        self.receiver.set_password('1234')
        self.receiver.save()
        self.mail = mommy.make(Mail, receiver=self.receiver, sender=self.sender)

    def test_send_mail(self):
        self.client.login(username='moein', password='1234')
        response = self.client.get(reverse("account:user_sent_messages"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["mails"][0], self.mail)
