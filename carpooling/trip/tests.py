from django.contrib.gis.geos import Point
from django.db.models import Q
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from account.models import Member
from group.models import Group, Membership
from trip.models import Trip, TripGroups, Companionship


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
        self.g1 = Group.objects.create(id=1, code='group1', title='group1', is_private=True,
                                       description='this is group1')
        self.g2 = Group.objects.create(id=2, code='group2', title='group2', is_private=False,
                                       description='this is group2')
        self.g3 = Group.objects.create(id=3, code='group3', title='group3', is_private=True,
                                       description='this is group3')
        self.g4 = Group.objects.create(id=4, code='group4', title='group4', is_private=False,
                                       description='this is group4')

        Membership.objects.create(member=self.mohsen, group=self.g1, role=Membership.MEMBER)
        Membership.objects.create(member=self.mohsen, group=self.g2, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.g3, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.g4, role=Membership.MEMBER)

        self.t1 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                      car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t2 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                      car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t3 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                      car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t4 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                      car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t5 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                      car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t6 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                      car_provider=self.ali, status=Trip.DONE_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())
        self.t7 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                      car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                      start_estimation=timezone.now(), end_estimation=timezone.now())

        Companionship.objects.create(trip=self.t4, member=self.mohsen, source=Point(5, 6), destination=Point(6, 7))
        Companionship.objects.create(trip=self.t6, member=self.mohsen, source=Point(5, 6), destination=Point(6, 7))

        TripGroups.objects.create(trip=self.t1, group=self.g1)
        TripGroups.objects.create(trip=self.t1, group=self.g3)
        TripGroups.objects.create(trip=self.t2, group=self.g1)
        TripGroups.objects.create(trip=self.t2, group=self.g2)
        TripGroups.objects.create(trip=self.t3, group=self.g2)
        TripGroups.objects.create(trip=self.t3, group=self.g4)
        TripGroups.objects.create(trip=self.t4, group=self.g3)
        TripGroups.objects.create(trip=self.t4, group=self.g4)
        TripGroups.objects.create(trip=self.t5, group=self.g1)
        TripGroups.objects.create(trip=self.t5, group=self.g4)
        TripGroups.objects.create(trip=self.t6, group=self.g2)
        TripGroups.objects.create(trip=self.t6, group=self.g3)

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


