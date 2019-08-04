from bs4 import BeautifulSoup as bs
from django.contrib.gis.geos import Point
from django.test import TestCase, Client
from django.utils import timezone

# Create your tests here.
from account.models import Member
from group.models import Group, Membership
from trip.models import Trip, TripGroups


class GetTripsTest(TestCase):
    c = Client(enforce_csrf_checks=False)

    def setUp(self):
        self.mohsen = Member.objects.create(username="mohsen")
        self.mohsen.set_password("12345678")
        self.mohsen.save()
        self.ali = Member.objects.create(username="alialavi")
        self.ali.set_password("12345678")
        self.ali.save()
        self.group1 = Group.objects.create(id=1, code='group1', title='group1', is_private=True,
                                           description='this is group1')
        self.group2 = Group.objects.create(id=2, code='group2', title='group2', is_private=False,
                                           description='this is group2')
        self.group3 = Group.objects.create(id=3, code='group3', title='group3', is_private=True,
                                           description='this is group3')
        self.group4 = Group.objects.create(id=4, code='group4', title='group4', is_private=False,
                                           description='this is group4')

        Membership.objects.create(member=self.mohsen, group=self.group1, role=Membership.MEMBER)
        Membership.objects.create(member=self.mohsen, group=self.group2, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.group3, role=Membership.MEMBER)
        Membership.objects.create(member=self.ali, group=self.group4, role=Membership.MEMBER)

        self.trip1 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                         car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())
        self.trip2 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                         car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())
        self.trip3 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                         car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())
        self.trip4 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=True,
                                         car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())
        self.trip5 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                         car_provider=self.mohsen, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())
        self.trip6 = Trip.objects.create(source=Point(3, 4), destination=Point(4, 5), is_private=False,
                                         car_provider=self.ali, status=Trip.WAITING_STATUS, capacity=4,
                                         start_estimation=timezone.now(), end_estimation=timezone.now())

        TripGroups.objects.create(trip=self.trip1, group=self.group1)
        TripGroups.objects.create(trip=self.trip1, group=self.group3)
        TripGroups.objects.create(trip=self.trip2, group=self.group1)
        TripGroups.objects.create(trip=self.trip2, group=self.group2)
        TripGroups.objects.create(trip=self.trip3, group=self.group2)
        TripGroups.objects.create(trip=self.trip3, group=self.group4)
        TripGroups.objects.create(trip=self.trip4, group=self.group3)
        TripGroups.objects.create(trip=self.trip4, group=self.group4)
        TripGroups.objects.create(trip=self.trip5, group=self.group1)
        TripGroups.objects.create(trip=self.trip5, group=self.group4)
        TripGroups.objects.create(trip=self.trip6, group=self.group2)
        TripGroups.objects.create(trip=self.trip6, group=self.group3)

    def test_get_owned_trips(self):
        self.c.logout()
        response = self.c.get('/trip/', follow=False)
        self.assertRedirects(response, '/account/login/?next=%2Ftrip%2F')
        self.c.login(username='mohsen', password='12345678')
        response = self.c.get('/trip/', follow=True)
        soup = bs(response.content)
        p1 = soup.find("p", {"id": self.trip1.id})
        p2 = soup.find("p", {"id": self.trip2.id})
        p3 = soup.find("p", {"id": self.trip3.id})
        p4 = soup.find("p", {"id": self.trip4.id})
        p5 = soup.find("p", {"id": self.trip5.id})
        p6 = soup.find("p", {"id": self.trip6.id})
        self.assertNotEqual(p1, None)
        self.assertNotEqual(p3, None)
        self.assertNotEqual(p5, None)
        self.assertEqual((p2, p4, p6), (None, None, None))

    def test_get_public_trips(self):
        self.c.logout()
        response = self.c.get('/trip/public/', follow=False)
        self.assertEqual(response.status_code, 200)
        self.c.login(username='mohsen', password='12345678')
        response = self.c.get('/trip/public/', follow=True)
        soup = bs(response.content)
        p1 = soup.find("p", {"id": self.trip1.id})
        p2 = soup.find("p", {"id": self.trip2.id})
        p3 = soup.find("p", {"id": self.trip3.id})
        p4 = soup.find("p", {"id": self.trip4.id})
        p5 = soup.find("p", {"id": self.trip5.id})
        p6 = soup.find("p", {"id": self.trip6.id})
        self.assertNotEqual(p1, None)
        self.assertNotEqual(p2, None)
        self.assertNotEqual(p5, None)
        self.assertNotEqual(p6, None)
        self.assertEqual((p3, p4), (None, None))

    def test_get_categorized_trips_without_public(self):
        self.c.logout()
        response = self.c.get('/trip/group/', follow=False)
        self.assertRedirects(response, '/account/login/?next=/trip/group/')

        self.c.login(username='mohsen', password='12345678')
        response = self.c.get('/trip/group/', follow=True)
        soup = bs(response.content)
        g1 = soup.find("p", {"id": 'group-' + str(self.group1.id)})
        g2 = soup.find("p", {"id": 'group-' + str(self.group2.id)})
        g3 = soup.find("p", {"id": 'group-' + str(self.group3.id)})
        g4 = soup.find("p", {"id": 'group-' + str(self.group4.id)})
        g1t1 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip1.id)})
        g1t2 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip2.id)})
        g1t5 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip5.id)})
        g2t2 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip2.id)})
        g2t3 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip3.id)})
        g2t6 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip6.id)})
        g4t3 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip3.id)})
        g4t4 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip4.id)})
        g4t5 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip5.id)})
        self.assertNotEqual(g1, None)
        self.assertNotEqual(g2, None)
        self.assertNotEqual(g1t1, None)
        self.assertNotEqual(g1t2, None)
        self.assertNotEqual(g1t5, None)
        self.assertNotEqual(g2t2, None)
        self.assertNotEqual(g2t3, None)
        self.assertNotEqual(g2t6, None)
        self.assertEqual((g3, g4), (None, None))
        self.assertEqual((g4t3, g4t4, g4t5), (None, None, None))

    def test_get_categorized_trips_with_public(self):
        self.c.logout()
        response = self.c.get('/trip/group/?include-public-groups=true', follow=False)
        self.assertRedirects(response, '/account/login/?next=/trip/group/%3Finclude-public-groups%3Dtrue')

        self.c.login(username='mohsen', password='12345678')
        response = self.c.get('/trip/group/?include-public-groups=true', follow=True)
        soup = bs(response.content)
        g1 = soup.find("p", {"id": 'group-' + str(self.group1.id)})
        g2 = soup.find("p", {"id": 'group-' + str(self.group2.id)})
        g3 = soup.find("p", {"id": 'group-' + str(self.group3.id)})
        g4 = soup.find("p", {"id": 'group-' + str(self.group4.id)})
        g1t1 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip1.id)})
        g1t2 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip2.id)})
        g1t5 = soup.find("p", {"id": 'group-' + str(self.group1.id) + '-trip-' + str(self.trip5.id)})
        g2t2 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip2.id)})
        g2t3 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip3.id)})
        g2t6 = soup.find("p", {"id": 'group-' + str(self.group2.id) + '-trip-' + str(self.trip6.id)})
        g3t1 = soup.find("p", {"id": 'group-' + str(self.group3.id) + '-trip-' + str(self.trip1.id)})
        g3t4 = soup.find("p", {"id": 'group-' + str(self.group3.id) + '-trip-' + str(self.trip4.id)})
        g3t6 = soup.find("p", {"id": 'group-' + str(self.group3.id) + '-trip-' + str(self.trip6.id)})
        g4t3 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip3.id)})
        g4t4 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip4.id)})
        g4t5 = soup.find("p", {"id": 'group-' + str(self.group4.id) + '-trip-' + str(self.trip5.id)})
        self.assertNotEqual(g1, None)
        self.assertNotEqual(g2, None)
        self.assertNotEqual(g4, None)
        self.assertNotEqual(g1t1, None)
        self.assertNotEqual(g1t2, None)
        self.assertNotEqual(g1t5, None)
        self.assertNotEqual(g2t2, None)
        self.assertNotEqual(g2t3, None)
        self.assertNotEqual(g2t6, None)
        self.assertNotEqual(g4t3, None)
        self.assertNotEqual(g4t4, None)
        self.assertNotEqual(g4t5, None)
        self.assertEqual(g3, None)
        self.assertEqual((g3t1, g3t4, g3t6), (None, None, None))

    def test_get_group_trips(self):
        self.c.logout()
        response = self.c.get('/trip/group/1/', follow=False)
        self.assertRedirects(response, '/account/login/')

        response = self.c.get('/trip/group/2/', follow=False)
        self.assertEqual(response.status_code, 200)

        response = self.c.get('/trip/group/5/', follow=False)
        self.assertEqual(response.status_code, 404)

        self.c.login(username='mohsen', password='12345678')

        response = self.c.get('/trip/group/1/', follow=True)
        soup = bs(response.content)
        p1 = soup.find("p", {"id": self.trip1.id})
        p2 = soup.find("p", {"id": self.trip2.id})
        p3 = soup.find("p", {"id": self.trip3.id})
        p4 = soup.find("p", {"id": self.trip4.id})
        p5 = soup.find("p", {"id": self.trip5.id})
        p6 = soup.find("p", {"id": self.trip6.id})
        self.assertNotEqual(p1, None)
        self.assertNotEqual(p2, None)
        self.assertNotEqual(p5, None)
        self.assertEqual((p3, p4, p6), (None, None, None))

        response = self.c.get('/trip/group/3/', follow=True)
        self.assertEqual(response.status_code, 403)

        response = self.c.get('/trip/group/5/', follow=False)
        self.assertEqual(response.status_code, 404)

    # path = 'active/'
    def test_get_active_trips(self):
        pass

    # path = 'all/'
    def test_get_available_trips(self):
        pass
