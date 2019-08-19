from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http import HttpResponseGone, HttpResponseForbidden, HttpResponseNotFound
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from model_mommy import mommy

from account.models import Member
from group.models import Group, Membership
from trip.models import Trip, TripGroups, Companionship, TripRequestSet, TripRequest, Vote
from trip.utils import SpotifyAgent


class TripCreationTest(TestCase):
    def setUp(self):
        self.moein = Member.objects.create(username="moein")
        self.moein.set_password("1234")
        self.moein.save()
        self.client = Client()
        self.client.login(username='moein', password='1234')

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
        self.moein = Member.objects.create(username="moein")
        self.moein.set_password("1234")
        self.moein.save()
        self.client = Client(enforce_csrf_checks=False)

    def test_get_public_trips(self):
        Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False, status=Trip.WAITING_STATUS,
                            capacity=4, start_estimation=timezone.now(), end_estimation=timezone.now())
        Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False, status=Trip.DONE_STATUS,
                            capacity=4, start_estimation=timezone.now(), end_estimation=timezone.now())
        Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True, status=Trip.WAITING_STATUS,
                            capacity=4, start_estimation=timezone.now(), end_estimation=timezone.now())

        response = self.client.get(reverse('trip:public_trips'), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(Trip.objects.filter(Q(is_private=False), ~Q(status=Trip.DONE_STATUS))), list(trips))

    def test_get_public_group_trips(self):
        g1 = Group.objects.create(id=1, code='group1', title='group1', is_private=False, description='this is group1')

        t1 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                 status=Trip.WAITING_STATUS, capacity=4, start_estimation=timezone.now(),
                                 end_estimation=timezone.now())
        t2 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                 status=Trip.DONE_STATUS, capacity=4, start_estimation=timezone.now(),
                                 end_estimation=timezone.now())
        t3 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                 status=Trip.WAITING_STATUS, capacity=4, start_estimation=timezone.now(),
                                 end_estimation=timezone.now())
        TripGroups.objects.create(trip=t1, group=g1)
        TripGroups.objects.create(trip=t2, group=g1)

        self.client.login(username=self.moein.username, password='1234')
        response = self.client.get(reverse('trip:group_trip', kwargs={'group_id': g1.id}), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        self.assertEqual(list(g1.trip_set.all()), list(trips))

    def test_get_not_existing_group_trips(self):
        self.client.login(username=self.moein.username, password='1234')
        response = self.client.get(reverse('trip:group_trip', kwargs={'group_id': 5}), follow=False)
        self.assertEqual(response.status_code, 404)


class GetTripsWithAuthenticatedUserTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.mohsen = Member.objects.create(username="mohsen")
        self.mohsen.set_password("12345678")
        self.mohsen.save()
        self.ali = Member.objects.create(username="alialavi")
        self.ali.set_password("12345678")
        self.ali.save()

        self.g1 = mommy.make(Group, id=1, is_private=True)
        self.g2 = mommy.make(Group, id=2, is_private=False)
        self.g3 = mommy.make(Group, id=3, is_private=True)
        self.g4 = mommy.make(Group, id=4, is_private=False)

        Membership.objects.create(member=self.mohsen, group=self.g1, role=Membership.MEMBER)
        Membership.objects.create(member=self.mohsen, group=self.g2, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.g3, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.g4, role=Membership.MEMBER)

        t1 = mommy.make(Trip, is_private=False, car_provider=self.mohsen, status=Trip.WAITING_STATUS)
        t2 = mommy.make(Trip, is_private=False, car_provider=self.ali, status=Trip.WAITING_STATUS)
        t3 = mommy.make(Trip, is_private=True, car_provider=self.mohsen, status=Trip.WAITING_STATUS)
        t4 = mommy.make(Trip, is_private=True, car_provider=self.ali, status=Trip.WAITING_STATUS)
        t5 = mommy.make(Trip, is_private=False, car_provider=self.mohsen, status=Trip.WAITING_STATUS)
        t6 = mommy.make(Trip, is_private=False, car_provider=self.ali, status=Trip.DONE_STATUS)
        t7 = mommy.make(Trip, is_private=True, car_provider=self.ali, status=Trip.WAITING_STATUS)

        Companionship.objects.create(trip=t4, member=self.mohsen, source=Point(5, 6), destination=Point(6, 7))
        Companionship.objects.create(trip=t6, member=self.mohsen, source=Point(5, 6), destination=Point(6, 7))

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

        self.c.login(username='mohsen', password='12345678')

    def test_get_owned_trips(self):
        response = self.c.get(reverse('trip:owned_trips'), follow=True)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        user = self.mohsen
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
        user = self.mohsen
        self.assertEqual(list(user.group_set.all()), list(groups))

    def test_get_categorized_trips_with_public(self):
        response = self.c.get(reverse('trip:categorized_trips'), {"include-public-groups": 'true'}, follow=True)
        self.assertEqual(response.status_code, 200)
        groups = response.context['groups']
        user = self.mohsen
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
        user = self.mohsen
        self.assertEqual(list((user.driving_trips.all() | user.partaking_trips.all()).distinct().exclude(
            status=Trip.DONE_STATUS)), list(trips))

    def test_get_available_trips(self):
        response = self.c.get(reverse('trip:available_trips'), follow=False)
        self.assertEqual(response.status_code, 200)
        trips = response.context['trips']
        user = self.mohsen
        self.assertEqual(list((user.driving_trips.all() | user.partaking_trips.all() | Trip.objects.filter(
            is_private=False).all()).distinct().exclude(status=Trip.DONE_STATUS)), list(trips))


class SearchTripTest(TestCase):
    def setUp(self):
        self.temp_account = Member.objects.create(username="testuser", first_name="javad")
        self.temp_account.set_password('majid123')
        self.temp_account.save()

    def test_anonymous(self):
        response = self.client.get(path=reverse('trip:search_trips'))
        self.assertEqual(response.status_code, 302)

    def test_search_login(self):
        self.client.login(username='testuser', password='majid123')
        response = self.client.get(reverse('trip:search_trips'))
        self.assertEqual(response.status_code, 200)


class CreateTripRequestTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.car_provider = Member.objects.create(username="car_provider_user")
        self.car_provider.set_password("12345678")
        self.car_provider.save()
        self.applicant = Member.objects.create(username="applicant_user")
        self.applicant.set_password("12345678")
        self.applicant.save()

        self.trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS, capacity=2)
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

        self.assertRedirects(response, reverse('trip:trip', kwargs={'pk': self.trip.id}))

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

        self.assertRedirects(response, reverse('trip:trip', kwargs={'pk': self.trip.id}))

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
        self.assertRedirects(response, reverse('trip:trip', kwargs={'pk': self.trip.id}))
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
        self.assertEqual(response.status_code, HttpResponseGone().status_code)

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
        self.assertEqual(response.status_code, HttpResponseForbidden().status_code)


class ManageTripRequestsTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.car_provider = Member.objects.create(username="car_provider")
        self.car_provider.set_password("12345678")
        self.car_provider.save()

        self.applicant = Member.objects.create(username="applicant")
        self.applicant.set_password("12345678")
        self.applicant.save()

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

        self.assertEqual(response.status_code, HttpResponseNotFound().status_code)
        self.assertEqual(self.trip_request.status, TripRequest.PENDING_STATUS)
        self.assertFalse(self.trip_request.containing_set.closed)

    def test_decline_incorrect_trip_request_id(self):
        dummy_trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS)
        response = self.c.post(reverse('trip:trip_request', kwargs={'trip_id': dummy_trip.id}), {
            'type': 'PUT',
            'request_id': self.trip_request.id,
            'action': 'accept',
        })

        self.assertEqual(response.status_code, HttpResponseNotFound().status_code)
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


class ManageTripPageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.car_provider = Member.objects.create(username="car_provider")
        self.car_provider.set_password("12345678")
        self.car_provider.save()
        self.passenger = Member.objects.create(username="passenger")
        self.passenger.set_password("12345678")
        self.passenger.save()
        self.authenticated_user = Member.objects.create(username="authenticated_user")
        self.authenticated_user.set_password("12345678")
        self.authenticated_user.save()
        self.trip = mommy.make(Trip, car_provider=self.car_provider, status=Trip.WAITING_STATUS, capacity=2)
        Companionship.objects.create(member=self.passenger, trip=self.trip, source=self.trip.source, destination=self.trip.destination)

    def test_updating_status_by_provider(self):
        self.client.login(username="car_provider", password="12345678")
        post_data = {'type': 'PUT', 'action': 'update_status'}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip.status, self.trip.CLOSED_STATUS)
        self.trip.status = self.trip.DONE_STATUS
        self.trip.save()
        self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.assertEqual(self.trip.status, self.trip.DONE_STATUS)

    def test_updating_status_by_member(self):
        self.client.login(username="passenger", password="12345678")
        post_data = {'type': 'PUT', 'action': 'update_status'}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.trip.status, self.trip.WAITING_STATUS)

    def test_provider_leaving(self):
        self.client.login(username="car_provider", password="12345678")
        post_data = {'type': 'PUT', 'action': 'leave', 'user_id': self.car_provider.id}
        spotify_agent = SpotifyAgent()
        self.trip.playlist_id = spotify_agent.create_playlist('test_playlist')
        self.trip.save()
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip.car_provider, None)
        self.assertEqual(self.trip.playlist_id, None)
        self.assertEqual(self.trip.status, self.trip.CANCELED_STATUS)

    def test_passenger_leaving(self):
        self.client.login(username="passenger", password="12345678")
        post_data = {'type': 'PUT', 'action': 'leave', 'user_id': self.passenger.id}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.passenger not in self.trip.passengers.all())

    def test_member_leaving(self):
        self.client.login(username="authenticated_user", password="12345678")
        post_data = {'type': 'PUT', 'action': 'leave', 'user_id': self.authenticated_user.id}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.assertEqual(response.status_code, 400)

    def test_trip_opening_by_provider(self):
        self.client.login(username="car_provider", password="12345678")
        post_data = {'type': 'PUT', 'action': 'open_trip'}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.trip.status, self.trip.WAITING_STATUS)
        self.trip.status = self.trip.CLOSED_STATUS
        self.trip.save()
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.trip.status, self.trip.WAITING_STATUS)

    def test_trip_opening_by_member(self):
        self.client.login(username="passenger", password="12345678")
        post_data = {'type': 'PUT', 'action': 'open_trip'}
        self.trip.status = self.trip.CLOSED_STATUS
        self.trip.save()
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.trip.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.trip.status, self.trip.CLOSED_STATUS)

    def test_vote_member_not_in_trip(self):
        self.client.login(username="authenticated_user", password="12345678")
        post_data = {'receiver_id': self.passenger.id, 'rate': 5}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.assertEqual(response.status_code, 403)
        vote_exists = Vote.objects.filter(sender=self.authenticated_user, receiver=self.passenger, rate=5,
                                          trip=self.trip).exists()
        self.assertFalse(vote_exists)

    def test_vote_in_wrong_status(self):
        self.client.login(username="passenger", password="12345678")
        post_data = {'receiver_id': self.passenger.id, 'rate': 5}
        response = self.client.post(reverse('trip:trip', kwargs={'pk': self.trip.id}), post_data)
        self.assertEqual(response.status_code, 403)
        vote_exists = Vote.objects.filter(sender=self.authenticated_user, receiver=self.passenger, rate=5,
                                          trip=self.trip).exists()
        self.assertFalse(vote_exists)



