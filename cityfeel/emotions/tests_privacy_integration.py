from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from emotions.models import EmotionPoint, Comment
from map.models import Location

User = get_user_model()


class PrivacyLogicIntegrationTestCase(TestCase):
    """Testy integracyjne dla logiki prywatności EmotionPoints."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

    # --- Public vs Private EmotionPoints ---

    def test_public_emotion_visible_on_user_profile(self):
        """Test że publiczny EmotionPoint jest widoczny na profilu użytkownika."""
        # Utwórz publiczny emotion point
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        # Sprawdź widok profilu (filtruje publiczne emocje)
        from django.urls import reverse
        from django.test import Client

        client = Client()
        client.login(username='testuser', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        response = client.get(url)

        recent_emotions = list(response.context['recent_emotions'])
        self.assertIn(public_emotion, recent_emotions)

    def test_private_emotion_not_visible_on_user_profile(self):
        """Test że prywatny EmotionPoint NIE jest widoczny na profilu użytkownika."""
        # Utwórz prywatny emotion point
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='private'
        )

        # Sprawdź widok profilu
        from django.urls import reverse
        from django.test import Client

        client = Client()
        client.login(username='testuser', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        response = client.get(url)

        recent_emotions = list(response.context['recent_emotions'])
        self.assertEqual(len(recent_emotions), 0)

    def test_both_types_visible_on_map_api(self):
        """Test że oba typy (public i private) są widoczne na mapie (API locations)."""
        # Utwórz publiczny emotion point dla user
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        # Drugi użytkownik z różnymi emotion points
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )

        # Trzeci użytkownik
        user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )
        EmotionPoint.objects.create(
            user=user3,
            location=self.location,
            emotional_value=4,
            privacy_status='private'
        )

        # Sprawdź API locations (powinny być wszystkie emocje w statystykach)
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/locations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        self.assertIsNotNone(location_data)
        # avg = (5 + 3 + 4) / 3 = 4.0
        self.assertEqual(float(location_data['avg_emotional_value']), 4.0)
        # count = 3 (wszystkie)
        self.assertEqual(location_data['emotion_points_count'], 3)

    def test_both_types_affect_avg_emotional_value(self):
        """Test że oba typy wpływają na avg_emotional_value lokalizacji."""
        # Publiczny: 5, Prywatny: 1
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=1,
            privacy_status='private'
        )

        # Sprawdź API
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/locations/')

        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        # avg = (5 + 1) / 2 = 3.0
        self.assertEqual(float(location_data['avg_emotional_value']), 3.0)

    def test_public_emotion_visible_in_api_emotion_points(self):
        """Test że publiczny EmotionPoint jest widoczny w API /emotion-points/."""
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/emotion-points/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emotion_ids = [ep['id'] for ep in response.data['results']]
        self.assertIn(public_emotion.id, emotion_ids)

    def test_private_emotion_not_visible_in_api_emotion_points(self):
        """Test że prywatny EmotionPoint NIE jest widoczny w API /emotion-points/."""
        private_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='private'
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/emotion-points/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emotion_ids = [ep['id'] for ep in response.data['results']]
        self.assertNotIn(private_emotion.id, emotion_ids)

    # --- Comments visibility ---

    def test_comments_only_on_public_emotion_points(self):
        """Test że komentarze są tylko do publicznych EmotionPoints (w modelu dozwolone, ale w statystykach tylko publiczne)."""
        # Publiczny emotion point z komentarzem
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=public_emotion,
            content='Public comment'
        )

        # Prywatny emotion point z komentarzem
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        private_emotion = EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )
        Comment.objects.create(
            user=user2,
            emotion_point=private_emotion,
            content='Private comment'
        )

        # Sprawdź API locations - comments_count powinien być 1 (tylko publiczny)
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/locations/')

        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        self.assertIsNotNone(location_data)
        self.assertEqual(location_data['comments_count'], 1)

    def test_latest_comment_only_from_public_emotion_points(self):
        """Test że latest_comment w API locations pochodzi tylko z publicznych EmotionPoints."""
        # Prywatny emotion point z komentarzem (starszy)
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        private_emotion = EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )
        Comment.objects.create(
            user=user2,
            emotion_point=private_emotion,
            content='Private comment (older)'
        )

        # Publiczny emotion point z komentarzem (nowszy)
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=public_emotion,
            content='Public comment (newer)'
        )

        # Sprawdź API locations
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/locations/')

        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        self.assertIsNotNone(location_data)
        self.assertIsNotNone(location_data['latest_comment'])
        # Powinien być komentarz z publicznego emotion point
        self.assertIn('Public comment', location_data['latest_comment']['content'])

    def test_comments_count_only_public_emotion_points(self):
        """Test że comments_count w API locations liczy tylko komentarze z publicznych EmotionPoints."""
        # Publiczny emotion point z 2 komentarzami
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=public_emotion,
            content='Comment 1'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=public_emotion,
            content='Comment 2'
        )

        # Prywatny emotion point z 1 komentarzem (nie powinien być liczony)
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        private_emotion = EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )
        Comment.objects.create(
            user=user2,
            emotion_point=private_emotion,
            content='Private comment'
        )

        # Sprawdź API locations
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/locations/')

        location_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location.id),
            None
        )

        self.assertIsNotNone(location_data)
        # Powinno być 2 (tylko z publicznego)
        self.assertEqual(location_data['comments_count'], 2)
