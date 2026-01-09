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

        # Sprawdź że użytkownik jest zalogowany
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'newuser')

        # Sprawdź że przekierowano do mapy
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

        # Edytuj profil i dodaj avatar
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

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)

        # Sprawdź profil
        user.refresh_from_db()
        self.assertTrue(user.avatar)
        self.assertEqual(user.first_name, 'Jan')


class EmotionPointCreationFlowTestCase(TestCase):
    """Testy E2E dla tworzenia emotion points."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

    def test_add_public_emotion_visible_in_api_and_profile(self):
        """Test: Dodanie publicznej oceny → Widoczna w API → Widoczna na profilu."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Dodaj publiczną ocenę przez API
        data = {
            'location': {
                'coordinates': {
                    'latitude': 54.3520,
                    'longitude': 18.6466,
                }
            },
            'emotional_value': 5,
            'privacy_status': 'public'
        }
        response = client.post('/api/emotion-points/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź że widoczna w API /emotion-points/
        response_list = client.get('/api/emotion-points/')
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_list.data['results']), 1)

        # Sprawdź że widoczna na profilu
        from django.test import Client
        web_client = Client()
        web_client.login(username='testuser', password='testpass123')
        profile_url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        profile_response = web_client.get(profile_url)

        self.assertEqual(profile_response.context['public_emotions'], 1)
        recent_emotions = list(profile_response.context['recent_emotions'])
        self.assertEqual(len(recent_emotions), 1)

    def test_change_privacy_to_private_disappears_from_profile(self):
        """Test: Zmiana prywatności na private → Znika z profilu."""
        # Utwórz publiczną ocenę
        emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        # Sprawdź że jest na profilu
        from django.test import Client
        web_client = Client()
        web_client.login(username='testuser', password='testpass123')
        profile_url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})

        profile_response = web_client.get(profile_url)
        self.assertEqual(profile_response.context['public_emotions'], 1)

        # Zmień na private
        emotion.privacy_status = 'private'
        emotion.save()

        # Sprawdź że zniknęła z profilu
        profile_response2 = web_client.get(profile_url)
        self.assertEqual(profile_response2.context['public_emotions'], 0)
        self.assertEqual(profile_response2.context['private_emotions'], 1)
        recent_emotions = list(profile_response2.context['recent_emotions'])
        self.assertEqual(len(recent_emotions), 0)


class FriendshipFlowTestCase(TestCase):
    """Testy E2E dla systemu znajomych."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

    def test_send_accept_friendship_flow(self):
        """Test: User A wysyła zaproszenie → User B widzi w /requests/ → Akceptuje → Obaj widzą w /friends/."""
        client = APIClient()

        # User1 wysyła zaproszenie
        client.force_authenticate(user=self.user1)
        response = client.post('/api/friendship/', {'friend_id': self.user2.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        friendship_id = response.data['id']

        # User2 widzi w /requests/
        client.force_authenticate(user=self.user2)
        response = client.get('/api/friendship/requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], friendship_id)

        # User2 akceptuje
        response = client.patch(f'/api/friendship/{friendship_id}/', {'status': 'accepted'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Obaj widzą w /friends/
        response1 = client.get('/api/friends/')
        self.assertEqual(len(response1.data), 1)
        self.assertEqual(response1.data[0]['username'], 'user1')

        client.force_authenticate(user=self.user1)
        response2 = client.get('/api/friends/')
        self.assertEqual(len(response2.data), 1)
        self.assertEqual(response2.data[0]['username'], 'user2')

    def test_delete_friendship_disappears_for_both(self):
        """Test: User A usuwa znajomość → Relacja znika dla obu."""
        # Utwórz zaakceptowaną znajomość
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        client = APIClient()

        # User1 widzi znajomego
        client.force_authenticate(user=self.user1)
        response = client.get('/api/friends/')
        self.assertEqual(len(response.data), 1)

        # User1 usuwa znajomość
        response = client.delete(f'/api/friendship/{friendship.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # User1 nie widzi już znajomego
        response = client.get('/api/friends/')
        self.assertEqual(len(response.data), 0)

        # User2 też nie widzi
        client.force_authenticate(user=self.user2)
        response = client.get('/api/friends/')
        self.assertEqual(len(response.data), 0)


class LocationStatisticsFlowTestCase(TestCase):
    """Testy E2E dla statystyk lokalizacji."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

    def test_add_emotions_changes_avg_emotional_value(self):
        """Test: Dodanie emotion points → avg_emotional_value się zmienia → Widoczne w API locations."""
        client = APIClient()
        client.force_authenticate(user=self.user1)

        # Sprawdź początkowe statystyki (brak ocen)
        response = client.get('/api/locations/')
        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )
        self.assertIsNone(location_data['avg_emotional_value'])

        # Dodaj pierwszą ocenę
        EmotionPoint.objects.create(
            user=self.user1,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        response = client.get('/api/locations/')
        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )
        self.assertEqual(float(location_data['avg_emotional_value']), 5.0)

        # Dodaj drugą ocenę
        EmotionPoint.objects.create(
            user=self.user2,
            location=self.location,
            emotional_value=3,
            privacy_status='public'
        )

        response = client.get('/api/locations/')
        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )
        # avg = (5 + 3) / 2 = 4.0
        self.assertEqual(float(location_data['avg_emotional_value']), 4.0)


class CommentFlowTestCase(TestCase):
    """Testy E2E dla komentarzy."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

        self.emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

    def test_add_comment_visible_in_latest_comment(self):
        """Test: Dodanie komentarza → Widoczny w latest_comment."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        # Dodaj komentarz
        data = {
            'content': 'Test comment content',
            'point_id': self.emotion.id
        }
        response = client.post('/api/comments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź że widoczny w API locations latest_comment
        response = client.get('/api/locations/')
        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        self.assertIsNotNone(location_data['latest_comment'])
        self.assertIn('Test comment content', location_data['latest_comment']['content'])
        self.assertEqual(location_data['latest_comment']['username'], 'testuser')