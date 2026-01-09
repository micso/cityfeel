from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

from emotions.models import EmotionPoint
from map.models import Location

User = get_user_model()


class DeleteEmotionViewTestCase(TestCase):
    """Testy dla widoku delete_emotion."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = Client()

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

        # Lokalizacja testowa
        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

        # EmotionPoint należący do user1
        self.emotion1 = EmotionPoint.objects.create(
            user=self.user1,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

    def test_delete_own_emotion_point(self):
        """Test usunięcia własnego EmotionPoint (POST)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.post(url)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        self.assertRedirects(response, expected_url)

        # Sprawdź że EmotionPoint został usunięty
        self.assertEqual(EmotionPoint.objects.count(), 0)

    def test_redirect_to_location_detail_after_deletion(self):
        """Test przekierowania do location detail po usunięciu."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.post(url)

        expected_url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        self.assertRedirects(response, expected_url)

    def test_delete_other_user_emotion_point_forbidden(self):
        """Test próby usunięcia cudzego EmotionPoint (403 Forbidden)."""
        # user2 próbuje usunąć emocję user1
        self.client.login(username='user2', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.post(url)

        # Powinno zwrócić 403 Forbidden
        self.assertEqual(response.status_code, 403)

        # Sprawdź że EmotionPoint NIE został usunięty
        self.assertEqual(EmotionPoint.objects.count(), 1)

    def test_delete_nonexistent_emotion_point_404(self):
        """Test usunięcia nieistniejącego EmotionPoint (404)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': 99999})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_get_request_not_allowed(self):
        """Test że GET request nie jest dozwolony (405 Method Not Allowed - @require_POST)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.get(url)

        # @require_POST zwraca 405 dla GET
        self.assertEqual(response.status_code, 405)

        # Sprawdź że EmotionPoint NIE został usunięty
        self.assertEqual(EmotionPoint.objects.count(), 1)

    def test_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika (redirect do login)."""
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_emotion_deleted_from_database(self):
        """Test weryfikacji że EmotionPoint został usunięty z bazy."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        # Przed usunięciem
        self.assertTrue(EmotionPoint.objects.filter(pk=self.emotion1.pk).exists())

        response = self.client.post(url)

        # Po usunięciu
        self.assertFalse(EmotionPoint.objects.filter(pk=self.emotion1.pk).exists())

    def test_success_message_displayed(self):
        """Test że wyświetlany jest success message po usunięciu."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('emotions:delete', kwargs={'pk': self.emotion1.pk})

        response = self.client.post(url, follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('usunięta', str(messages[0]))
