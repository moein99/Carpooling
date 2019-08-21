from datetime import timezone

from dateutil.parser import parse
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponseGone, HttpResponseForbidden, HttpResponseNotFound
from django.test import TestCase, Client
from django.urls import reverse
from model_mommy import mommy

from account.models import Member, Mail
from group.models import Group, Membership
from trip.models import Trip, TripGroups, Companionship, TripRequestSet, TripRequest


class TripCreationTest(TestCase):
    def setUp(self):
        Member.objects.create_user(username='test_user', password='12345678')
        self.client = Client()
        self.client.login(username='test_user', password='12345678')

    def test_trip_creation(self):
        post_data = {'is_private': False, 'capacity': 18, 'start_estimation': '2006-10-25 14:30:57',
                     'end_estimation': '2006-10-25 14:30:58', 'source_lat': '13.2', 'source_lng': '15.2',
                     'destination_lat': '90', 'destination_lng': '14.23',
                     'trip_description': 'holy_test'}
        response = self.client.post(reverse('trip:trip_creation'), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_dates(self):
        post_data = {'is_private': False, 'capacity': 18, 'start_estimation': '2006-10-25 14:30:59',
                     'end_estimation': '2006-10-25 14:30:58', 'source_lat': '13.2', 'source_lng': '15.2',
                     'destination_lat': '-1', 'destination_lng': '14.23',
                     'trip_description': 'holy_test'}
        response = self.client.post(reverse('trip:trip_creation'), post_data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_invalid_capacity(self):
        post_data = {'is_private': False, 'capacity': 21, 'start_estimation': '2006-10-25 14:30:57',
                     'end_estimation': '2006-10-25 14:30:58', 'source_lat': '13.2', 'source_lng': '15.2',
                     'destination_lat': '-1', 'destination_lng': '14.23',
                     'trip_description': 'holy_test'}
        response = self.client.post(reverse('trip:trip_creation'), post_data, follow=True)
        self.assertEqual(response.status_code, 400)
        post_data['capacity'] = 0
        response = self.client.post(reverse('trip:trip_creation'), post_data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_invalid_point(self):
        post_data = {'is_private': False, 'capacity': 18, 'start_estimation': '2006-10-25 14:30:57',
                     'end_estimation': '2006-10-25 14:30:58', 'source_lat': '13.2', 'source_lng': '15.2',
                     'destination_lat': '-1', 'destination_lng': '-1',
                     'trip_description': 'holy_test'}
        response = self.client.post(reverse('trip:trip_creation'), post_data, follow=True)
        self.assertEqual(response.status_code, 400)


class GetTripsWithAnonymousUserTest(TestCase):
    def setUp(self):
        self.test_user = Member.objects.create_user(username='test_user', password='12345678')
        self.client = Client(enforce_csrf_checks=False)

    def test_get_public_trips(self):
        mommy.make(Trip, is_private=False, status=Trip.WAITING_STATUS)
        mommy.make(Trip, is_private=False, status=Trip.DONE_STATUS)
        mommy.make(Trip, is_private=True, status=Trip.WAITING_STATUS)

        response = self.client.get(reverse('trip:public_trips'), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))), list(trips))

    def test_get_public_group_trips(self):
        g1 = mommy.make(Group, is_private=False)

        t1 = mommy.make(Trip, is_private=False, status=Trip.WAITING_STATUS)
        t2 = mommy.make(Trip, is_private=False, status=Trip.DONE_STATUS)
        t3 = mommy.make(Trip, is_private=True, status=Trip.WAITING_STATUS)

        TripGroups.objects.create(trip=t1, group=g1)
        TripGroups.objects.create(trip=t2, group=g1)

        self.client.login(username=self.test_user.username, password='12345678')
        response = self.client.get(reverse('trip:group_trip', kwargs={'group_id': g1.id}), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(g1.trip_set.all()), list(trips))

    def test_get_not_existing_group_trips(self):
        self.client.login(username=self.test_user.username, password='12345678')
        response = self.client.get(reverse('trip:group_trip', kwargs={'group_id': 5}), follow=False)
        self.assertEqual(response.status_code, 404)


class GetTripsWithAuthenticatedUserTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.test_user_1 = Member.objects.create_user(username='test_user_1', password='12345678')
        self.test_user_2 = Member.objects.create_user(username='test_user_2', password='12345678')

        self.g1 = mommy.make(Group, id=1, is_private=True)
        self.g2 = mommy.make(Group, id=2, is_private=False)
        self.g3 = mommy.make(Group, id=3, is_private=True)
        self.g4 = mommy.make(Group, id=4, is_private=False)

        Membership.objects.create(member=self.test_user_1, group=self.g1, role=Membership.MEMBER)
        Membership.objects.create(member=self.test_user_1, group=self.g2, role=Membership.MEMBER)
        Membership.objects.create(member=self.test_user_2, group=self.g3, role=Membership.MEMBER)
        Membership.objects.create(member=self.test_user_2, group=self.g4, role=Membership.MEMBER)

        t1 = mommy.make(Trip, is_private=False, car_provider=self.test_user_1, status=Trip.WAITING_STATUS)
        t2 = mommy.make(Trip, is_private=False, car_provider=self.test_user_2, status=Trip.WAITING_STATUS)
        t3 = mommy.make(Trip, is_private=True, car_provider=self.test_user_1, status=Trip.WAITING_STATUS)
        t4 = mommy.make(Trip, is_private=True, car_provider=self.test_user_2, status=Trip.WAITING_STATUS)
        t5 = mommy.make(Trip, is_private=False, car_provider=self.test_user_1, status=Trip.WAITING_STATUS)
        t6 = mommy.make(Trip, is_private=False, car_provider=self.test_user_2, status=Trip.DONE_STATUS)
        t7 = mommy.make(Trip, is_private=True, car_provider=self.test_user_2, status=Trip.WAITING_STATUS)

        Companionship.objects.create(trip=t4, member=self.test_user_1, source=Point(5, 6), destination=Point(6, 7))
        Companionship.objects.create(trip=t6, member=self.test_user_1, source=Point(5, 6), destination=Point(6, 7))

        TripGroups.objects.create(trip=t1, group=self.g1)
        TripGroups.objects.create(trip=t1, group=self.g3)
        TripGroups.objects.create(trip=t2, group=self.g1)
        TripGroups.objects.create(trip=t2, group=self.g2)
        TripGroups.objects.create(trip=t3, group=self.g2)
        TripGroups.objects.create(trip=t3, group=self.g4)
        TripGroups.objects.create(trip=t4, group=self.g3)
        TripGroups.objects.create(trip=t4, group=self.g4)
        TripGroups.objects.create(trip=t5, group=self.g1)
        TripGroups.objects.create(trip=t5, group=self.g4)
        TripGroups.objects.create(trip=t6, group=self.g2)
        TripGroups.objects.create(trip=t6, group=self.g3)

        self.c.login(username='test_user_1', password='12345678')

    def test_get_owned_trips(self):
        response = self.c.get(reverse('trip:owned_trips'), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        user = self.test_user_1
        self.assertEqual(list(user.driving_trips.all()), list(trips))

    def test_get_public_trips(self):
        response = self.c.get(reverse('trip:public_trips'), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))), list(trips))

    def test_get_categorized_trips_without_public(self):
        response = self.c.get(reverse('trip:categorized_trips'), follow=True)
        self.assertEqual(response.status_code, 200)
        groups = response.context['groups']
        user = self.test_user_1
        self.assertEqual(list(user.group_set.all()), list(groups))

    def test_get_categorized_trips_with_public(self):
        response = self.c.get(reverse('trip:categorized_trips'), {"include-public-groups": 'true'}, follow=True)
        self.assertEqual(response.status_code, 200)
        groups = response.context['groups']
        user = self.test_user_1
        self.assertEqual(list((user.group_set.all() | Group.objects.filter(is_private=False)).distinct()), list(groups))

    def test_get_participating_group_trips(self):
        response = self.c.get(reverse('trip:group_trip', kwargs={'group_id': 1}), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(self.g1.trip_set.all()), list(trips))

    def test_get_not_participating_group_trips(self):
        response = self.c.get(reverse('trip:group_trip', kwargs={'group_id': 3}), follow=True)
        self.assertEqual(response.status_code, 403)

    def test_get_public_group_trips(self):
        response = self.c.get(reverse('trip:group_trip', kwargs={'group_id': 4}), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(self.g4.trip_set.all()), list(trips))

    def test_get_not_existing_group_trips(self):
        response = self.c.get(reverse('trip:group_trip', kwargs={'group_id': 5}), follow=True)
        self.assertEqual(response.status_code, 404)

    def test_get_active_trips(self):
        response = self.c.get(reverse('trip:active_trips'), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        user = self.test_user_1
        self.assertEqual(list((user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(
            status=Trip.DONE_STATUS)), list(trips))

    def test_get_available_trips(self):
        response = self.c.get(reverse('trip:available_trips'), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        user = self.test_user_1
        self.assertEqual(list((user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
            is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)), list(trips))


class SearchTripTest(TestCase):
    def setUp(self):
        self.test_user = Member.objects.create_user(username="test_user", password='12345678')

    def test_anonymous(self):
        response = self.client.get(path=reverse('trip:search_trips'))
        self.assertEqual(response.status_code, 302)

    def test_search_login(self):
        self.client.login(username='test_user', password='12345678')
        response = self.client.get(reverse('trip:search_trips'))
        self.assertEqual(response.status_code, 200)


class CreateTripRequestTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.car_provider = Member.objects.create_user(username='car_provider_user', password='12345678')
        self.applicant = Member.objects.create_user(username='applicant_user', password='12345678')

        self.trip = mommy.make(Trip, is_private=True, car_provider=self.car_provider, status=Trip.WAITING_STATUS,
                               capacity=2)
        group = mommy.make(Group)
        mommy.make(TripGroups, trip=self.trip, group=group)
        mommy.make(Membership, member=self.applicant, group=group)
        self.c.login(username='applicant_user', password='12345678')

    def test_get_trip_request_form(self):
        response = self.c.get(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}))
        self.assertTemplateUsed(response, 'join_trip.html')

    def test_new_request_set(self):
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
            'new_request_set_title': 'Title',
        })

        self.assertRedirects(response, reverse('trip:trip', kwargs={'trip_id': self.trip.id}))

        new_trip_request_set = TripRequestSet.objects.get(title='Title')
        new_trip_request = TripRequest.objects.get(trip=self.trip)
        self.assertEqual(new_trip_request.containing_set, new_trip_request_set)

    def test_existing_request_set(self):
        trip_request_set = TripRequestSet.objects.create(title='Title', applicant=self.applicant)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': False,
            'containing_set': trip_request_set.id,
        })

        self.assertRedirects(response, reverse('trip:trip', kwargs={'trip_id': self.trip.id}))

        new_trip_request = TripRequest.objects.get(trip=self.trip)
        self.assertEqual(new_trip_request.containing_set, trip_request_set)

    def test_without_request_set(self):
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': False,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'join_trip.html')
        self.assertFalse(TripRequest.objects.filter(trip=self.trip).exists())

    def test_closed_request_set(self):
        trip_request_set = TripRequestSet.objects.create(title='Title', applicant=self.applicant, closed=True)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': False,
            'containing_set': trip_request_set.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'join_trip.html')
        self.assertFalse(TripRequest.objects.filter(trip=self.trip).exists())

    def test_no_title_new_request_set(self):
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
        })
        self.assertRedirects(response, reverse('trip:trip', kwargs={'trip_id': self.trip.id}))
        self.assertTrue(TripRequestSet.objects.filter(title='No Title').exists())

    def test_not_waiting_trip(self):
        self.trip.status = Trip.IN_ROUTE_STATUS
        self.trip.save()
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
            'new_request_set_title': 'Title'
        })
        self.assertEqual(response.status_code, HttpResponseGone.status_code)

    def test_not_accessible_trip(self):
        Membership.objects.filter(member=self.applicant).delete()
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
            'new_request_set_title': 'Title'
        })
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_car_provider_request(self):
        self.c.login(username='car_provider_user', password='12345678')
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
            'new_request_set_title': 'Title'
        })
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

    def test_automatically_joinable_trip(self):
        self.trip.people_can_join_automatically = True
        self.trip.save()

        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'source_lat': '34',
            'source_lng': '34',
            'destination_lat': '34',
            'destination_lng': '34',
            'create_new_request_set': True,
            'new_request_set_title': 'Title',
        })

        self.assertRedirects(response, reverse('trip:trip', kwargs={'trip_id': self.trip.id}))

        new_trip_request_set = TripRequestSet.objects.get(title='Title')
        new_trip_request = TripRequest.objects.get(containing_set=new_trip_request_set, trip=self.trip)

        self.assertEqual(new_trip_request.containing_set, new_trip_request_set)
        self.assertEqual(new_trip_request.status, TripRequest.ACCEPTED_STATUS)
        self.assertTrue(new_trip_request_set.closed)
        self.assertTrue(Companionship.objects.filter(member=self.applicant, trip=self.trip).exists())


class ManageTripRequestsTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.car_provider = Member.objects.create_user(username='car_provider', password='12345678')
        self.applicant = Member.objects.create_user(username='applicant', password='12345678')

        self.trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS, capacity=2)
        self.trip_request_set = TripRequestSet.objects.create(title='Title', applicant=self.applicant)
        self.trip_request = mommy.make(TripRequest, trip=self.trip, containing_set=self.trip_request_set)

        self.c.login(username='car_provider', password='12345678')

    def test_get_trip_requests_list(self):
        response = self.c.get(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}))
        self.assertTemplateUsed(response, 'trip_requests.html')

    def test_valid_accept_trip_request(self):
        dummy_trip_request = mommy.make(TripRequest, trip=self.trip, containing_set=self.trip_request_set)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })
        self.trip_request = TripRequest.objects.get(id=self.trip_request.id)
        dummy_trip_request = TripRequest.objects.get(id=dummy_trip_request.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip_request.status, TripRequest.ACCEPTED_STATUS)
        self.assertEqual(dummy_trip_request.status, TripRequest.CANCELED_STATUS)
        self.assertTrue(self.trip_request.containing_set.closed)
        self.assertTrue(Companionship.objects.filter(trip=self.trip, member=self.applicant).exists())

    def test_valid_decline_trip_request(self):
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'decline',
        })
        self.trip_request = TripRequest.objects.get(id=self.trip_request.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip_request.status, TripRequest.DECLINED_STATUS)

    def test_accept_full_trip_request(self):
        for i in range(self.trip.capacity):
            mommy.make(Companionship, trip=self.trip, member=mommy.make(Member))
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip_request.status, TripRequest.PENDING_STATUS)
        self.assertFalse(self.trip_request.containing_set.closed)
        self.assertEqual(response.context['error'], 'Trip is full')

    def test_accept_incorrect_trip_request_id(self):
        dummy_trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': dummy_trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })

        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)
        self.assertEqual(self.trip_request.status, TripRequest.PENDING_STATUS)
        self.assertFalse(self.trip_request.containing_set.closed)

    def test_decline_incorrect_trip_request_id(self):
        dummy_trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': dummy_trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })

        self.assertEqual(response.status_code, HttpResponseNotFound.status_code)
        self.assertEqual(self.trip_request.status, TripRequest.PENDING_STATUS)

    def test_manage_requests_by_none_car_provider(self):
        self.c.login(username='applicant', password='12345678')
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)

        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': self.trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })
        self.assertEqual(response.status_code, HttpResponseForbidden.status_code)


class AutomaticallyJoinTripTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.car_provider = Member.objects.create_user(username='car_provider', password='12345678')
        self.applicant = Member.objects.create_user(username='applicant', password='12345678')

        self.trip = mommy.make(Trip, car_provider=self.car_provider, people_can_join_automatically=True,
                               status=Trip.WAITING_STATUS, capacity=2, source=Point(34, 44), destination=Point(44, 54),
                               start_estimation=parse('2006-10-25 13:30:57'),
                               end_estimation=parse('2006-10-25 14:30:57'))
        self.c.login(username='applicant', password='12345678')

    def test_get_automatically_join_trip_form(self):
        response = self.c.get(reverse('trip:automatically_join_trip'))
        self.assertTemplateUsed(response, 'automatically_join_trip_form.html')

    def test_automatically_join_nearby_in_time_range_trip(self):
        response = self.c.post(reverse('trip:automatically_join_trip'), {
            'source_lat': '34',
            'source_lng': '44',
            'destination_lat': '44',
            'destination_lng': '54',
            'start_estimation': '2006-10-25 14:15:57',
            'end_estimation': '2006-10-25 15:30:58',
        })

        self.assertRedirects(response, reverse('trip:trip', kwargs={'trip_id': self.trip.id}))

    def test_automatically_join_nearby_out_of_time_range_trip(self):
        response = self.c.post(reverse('trip:automatically_join_trip'), {
            'source_lat': '34',
            'source_lng': '44',
            'destination_lat': '44',
            'destination_lng': '54',
            'start_estimation': '2006-10-25 15:15:57',
            'end_estimation': '2006-10-25 15:30:58',
        })

        self.assertTemplateUsed(response, 'trip_not_found.html')

    def test_automatically_join_out_of_range_trip(self):
        response = self.c.post(reverse('trip:automatically_join_trip'), {
            'source_lat': '80',
            'source_lng': '80',
            'destination_lat': '80',
            'destination_lng': '80',
            'start_estimation': '2006-10-25 14:15:57',
            'end_estimation': '2006-10-25 15:30:58',
        })

        self.assertTemplateUsed(response, 'trip_not_found.html')


class QuickMessageTest(TestCase):
    def setUp(self):
        self.driver = Member.objects.create_user(username='test_user', password='12345678')
        self.client = Client()
        self.test_trip_waiting = mommy.make(Trip, car_provider=self.driver, status=Trip.WAITING_STATUS)
        self.test_trip_in_route = mommy.make(Trip, car_provider=self.driver, status=Trip.WAITING_STATUS)
        self.client.login(username='test_user', password='12345678')
        self.passenger = Member.objects.create_user(username='test_user2', password='12345678')
        self.second_passenger = Member.objects.create_user(username='test_user3', password='12345678')

    def get_request_not_in_route(self):
        self.client.login(username='test_user', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_waiting)
        response = self.client.get(
            reverse("trip:trip_quick_message",
                    kwargs={'trip_id': self.test_trip_waiting.id, 'user_id': self.passenger.id}))
        self.assertEqual(response.status_code, 400)

    def get_request_not_a_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        response = self.client.get(
            reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.driver}))
        self.assertEqual(response.status_code, 400)

    def get_request_passenger_to_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        mommy.make(Companionship, member=self.second_passenger, trip=self.test_trip_in_route)
        response = self.client.get(
            reverse("trip:trip_quick_message",
                    kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.second_passenger}))
        self.assertEqual(response.status_code, 400)

    def get_request_as_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        response = self.client.get(
            reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.driver}))
        self.assertEqual(response.status_code, 200)

    def get_request_as_driver(self):
        self.client.login(username='test_user', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        response = self.client.get(
            reverse("trip:trip_quick_message",
                    kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.passenger}))
        self.assertEqual(response.status_code, 200)

    def post_request_as_driver(self):
        self.client.login(username='test_user', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        response = self.client.get(reverse("trip:trip_quick_message",
                                           kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.passenger}),
                                   {'message': "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Mail.objects.filter(receiver=self.passenger, message="test").exists())

    def post_request_as_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        response = self.client.post(
            reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.driver}),
            {'message': "test"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Mail.objects.filter(receiver=self.driver, message="test").exists())

    def post_request_not_in_route(self):
        self.client.login(username='test_user', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_waiting)
        response = self.client.post(reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_waiting.id,
                                                                               'user_id': self.passenger.id}),
                                    {'message': "test"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Mail.objects.filter(receiver=self.passenger, message="test").exists())

    def post_request_not_a_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        response = self.client.post(
            reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_in_route.id, 'user_id': self.driver}),
            {'message': "test"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Mail.objects.filter(receiver=self.driver, message="test").exists())

    def post_request_passenger_to_passenger(self):
        self.client.login(username='test_user2', password='12345678')
        mommy.make(Companionship, member=self.passenger, trip=self.test_trip_in_route)
        mommy.make(Companionship, member=self.second_passenger, trip=self.test_trip_in_route)
        response = self.client.post(reverse("trip:trip_quick_message", kwargs={'trip_id': self.test_trip_in_route.id,
                                                                               'user_id': self.second_passenger}),
                                    {"message": "test"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Mail.objects.filter(receiver=self.passenger, message="test").exists())
