# from django.test import TestCase, Client
# from django.urls import reverse
# import json
# from search import index as INDEX
# from account.models import Member
# from model_mommy import mommy

# TODO: need to create users in elasticsearch database

# class SearchPeopleTest(TestCase):
#     def setUp(self):
#         test_user_1 = mommy.make(Member, username='moein', _fill_optional=['email'])
#         test_user_1.set_password('1234')
#         test_user_1.save()
#         self.test_user_2 = mommy.make(Member, username='sepehr', password='1234', _fill_optional=['email'])
#         self.test_user_3 = mommy.make(Member, username='sajjad', password='1234', _fill_optional=['email'])
#         self.test_user_4 = mommy.make(Member, username='sepi', password='1234', _fill_optional=['email'])
#         INDEX.index_profile({
#             "id": self.test_user_2.id
#         })
#         self.client = Client()
#
#     def test_search_members(self):
#         self.client.login(username="moein", password="1234")
#         response = self.client.get(reverse('root:search_people', kwargs={"query": 'se'}))
#         response_in_json = json.loads(response.content)
#         result_people_user_names = [person['user_name'] for person in response_in_json['people']]
#         self.assertTrue('sepehr' in result_people_user_names and
#                         'sepi' in result_people_user_names and
#                         not 'sajjad' in result_people_user_names)
