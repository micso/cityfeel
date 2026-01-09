from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from emotions.models import EmotionPoint, Comment
from map.models import Location
from auth.models import Friendship

User = get_user_model()


class UserRegistrationAndProfileFlowTestCase(TestCase):
    """Testy E2E dla rejestracji użytkownika i profilu."""

    def test_registration_auto_login_redirect_flow(self):
        """Test: Rejestracja → Auto-login → Redirect do mapy."""
        client = Client()
        url = reverse('cf_auth:register')

        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = client.post(url, data, follow=True)

        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'newuser')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'map/emotion_map.html')

    def test_edit_profile_upload_avatar_visible_on_profile(self):
        """Test: Edycja profilu → Upload avatar → Widoczny na profilu."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        client = Client()
        client.login(username='testuser', password='testpass123')

        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile

        image = Image.new('RGB', (100, 100), color='blue')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        avatar_file = SimpleUploadedFile(
            name='avatar.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

        edit_url = reverse('cf_auth:profile_edit')
        data = {
            'email': 'test@example.com',
            'first_name': 'Jan',
            'last_name': 'Kowalski',
        }
        response = client.post(edit_url, data={'avatar': avatar_file, **data})

        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.avatar)
        self.assertEqual(user.first_name, 'Jan')


class EmotionPointCreationFlowTestCase(TestCase):
    """Testy E2E dla tworzenia emotion points."""

    def setUp(self):
        self.user = User.objects.create_user('testuser', 't@e.com', 'pass')
        self.location = Location.objects.create(name='Test Loc', coordinates=Point(18.6, 54.3))

    def test_add_public_emotion_visible_in_api_and_profile(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        data = {
            'location': {'coordinates': {'latitude': 54.3, 'longitude': 18.6}},
            'emotional_value': 5,
            'privacy_status': 'public'
        }
        response = client.post('/api/emotion-points/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_list = client.get('/api/emotion-points/')
        self.assertEqual(len(response_list.data['results']), 1)

        web_client = Client()
        web_client.login(username='testuser', password='pass')
        profile_url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        profile_response = web_client.get(profile_url)

        self.assertEqual(profile_response.context['public_emotions'], 1)

    def test_change_privacy_to_private_disappears_from_profile(self):
        emotion = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=5, privacy_status='public'
        )
        web_client = Client()
        web_client.login(username='testuser', password='pass')
        profile_url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})

        # Check public
        self.assertEqual(web_client.get(profile_url).context['public_emotions'], 1)

        # Change to private
        emotion.privacy_status = 'private'
        emotion.save()

        # Check hidden
        resp = web_client.get(profile_url)
        self.assertEqual(resp.context['public_emotions'], 0)
        self.assertEqual(resp.context['private_emotions'], 1)


class FriendshipFlowTestCase(TestCase):
    """Testy E2E dla systemu znajomych."""

    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'u1@e.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'u2@e.com', 'pass')

    def test_send_accept_friendship_flow(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)
        response = client.post('/api/friendship/', {'friend_id': self.user2.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        friendship_id = response.data['id']

        client.force_authenticate(user=self.user2)
        response = client.patch(f'/api/friendship/{friendship_id}/', {'status': 'accepted'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = client.get('/api/friends/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'user1')

    def test_delete_friendship_disappears_for_both(self):
        friendship = Friendship.objects.create(user=self.user1, friend=self.user2, status=Friendship.ACCEPTED)
        client = APIClient()
        client.force_authenticate(user=self.user1)

        response = client.delete(f'/api/friendship/{friendship.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(len(client.get('/api/friends/').data), 0)

        client.force_authenticate(user=self.user2)
        self.assertEqual(len(client.get('/api/friends/').data), 0)


class LocationStatisticsFlowTestCase(TestCase):
    """Testy E2E dla statystyk lokalizacji."""

    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'u1@e.com', 'pass')
        self.location = Location.objects.create(name='Loc', coordinates=Point(18.6, 54.3))

    def test_add_emotions_changes_avg_emotional_value(self):
        client = APIClient()
        client.force_authenticate(user=self.user1)

        EmotionPoint.objects.create(user=self.user1, location=self.location, emotional_value=5)

        response = client.get('/api/locations/')
        loc = next(l for l in response.data['results'] if l['id'] == self.location.id)
        self.assertEqual(float(loc['avg_emotional_value']), 5.0)


class CommentFlowTestCase(TestCase):
    """Testy E2E dla komentarzy."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='t@e.com', password='pass')
        self.location = Location.objects.create(name='Test Loc', coordinates=Point(18.6, 54.3))
        # Opcjonalnie: user ocenił miejsce
        EmotionPoint.objects.create(user=self.user, location=self.location, emotional_value=5, privacy_status='public')

    def test_add_comment_visible_in_latest_comment(self):
        """Test: Dodanie komentarza → Widoczny w latest_comment."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        data = {
            'content': 'Test comment content',
            'location_id': self.location.id  # [FIX] location_id zamiast point_id
        }
        response = client.post('/api/comments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = client.get('/api/locations/')
        location_data = next((loc for loc in response.data['results'] if loc['id'] == self.location.id), None)

        self.assertIsNotNone(location_data['latest_comment'])
        self.assertIn('Test comment content', location_data['latest_comment']['content'])
        self.assertEqual(location_data['latest_comment']['username'], 'testuser')