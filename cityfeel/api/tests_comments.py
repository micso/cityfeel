from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status
from emotions.models import EmotionPoint, Comment
from map.models import Location

User = get_user_model()

class CommentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user('u1', 'u1@e.com', 'pass')
        self.location = Location.objects.create(name='Loc', coordinates=Point(18.6, 54.3))
        self.url = '/api/comments/'

    def test_create_comment_success(self):
        self.client.force_authenticate(user=self.user1)
        data = {'content': 'Super!', 'location_id': self.location.id} # [FIX] location_id
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().location, self.location)

    def test_create_comment_missing_content(self):
        self.client.force_authenticate(user=self.user1)
        data = {'location_id': self.location.id}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_comment_missing_location_id(self):
        self.client.force_authenticate(user=self.user1)
        data = {'content': 'Test'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location_id', response.data)

    def test_create_comment_nonexistent_location(self):
        self.client.force_authenticate(user=self.user1)
        data = {'content': 'Test', 'location_id': 999}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_automatically_assigned(self):
        self.client.force_authenticate(user=self.user1)
        data = {'content': 'Test', 'location_id': self.location.id}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'u1')