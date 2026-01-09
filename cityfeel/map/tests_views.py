from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import io
from PIL import Image

from map.models import Location
from emotions.models import EmotionPoint, Photo

User = get_user_model()


class EmotionMapViewTestCase(TestCase):
    """Testy dla widoku EmotionMapView."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('map:emotion_map')

    def test_get_emotion_map_view(self):
        """Test GET zwraca template map/emotion_map.html."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'map/emotion_map.html')

    def test_context_contains_proximity_radius_setting(self):
        """Test że context zawiera settings.CITYFEEL_LOCATION_PROXIMITY_RADIUS."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)

        self.assertIn('settings', response.context)
        self.assertIn('CITYFEEL_LOCATION_PROXIMITY_RADIUS', response.context['settings'])
        self.assertEqual(
            response.context['settings']['CITYFEEL_LOCATION_PROXIMITY_RADIUS'],
            settings.CITYFEEL_LOCATION_PROXIMITY_RADIUS
        )

    def test_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class LocationDetailViewTestCase(TestCase):
    """Testy dla widoku LocationDetailView."""

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

        self.url = reverse('map:location_detail', kwargs={'pk': self.location.pk})

    # --- GET tests ---

    def test_get_location_detail(self):
        """Test wyświetlenia szczegółów lokalizacji."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'map/location_detail.html')
        self.assertEqual(response.context['location'], self.location)

    def test_context_contains_public_points(self):
        """Test że context zawiera public_points - tylko publiczne EmotionPoints."""
        # Publiczny i prywatny emotion point
        public_emotion = EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location,
            emotional_value=3, privacy_status='private'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        public_points = list(response.context['public_points'])
        self.assertEqual(len(public_points), 1)
        self.assertEqual(public_points[0], public_emotion)

    def test_public_points_sorted_by_created_at_desc(self):
        """Test że public_points są posortowane po -created_at."""
        ep1 = EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=4, privacy_status='public'
        )
        ep2 = EmotionPoint.objects.create(
            user=self.user2, location=self.location,
            emotional_value=5, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        public_points = list(response.context['public_points'])
        # Najnowszy powinien być pierwszy (ep2)
        self.assertEqual(public_points[0], ep2)
        self.assertEqual(public_points[1], ep1)

    def test_context_contains_photos(self):
        """Test że context zawiera photos - sorted by -created_at."""
        photo1 = Photo.objects.create(
            location=self.location,
            image='test1.jpg',
            caption='First photo'
        )
        photo2 = Photo.objects.create(
            location=self.location,
            image='test2.jpg',
            caption='Second photo'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        photos = list(response.context['photos'])
        self.assertEqual(len(photos), 2)
        # Najnowsze powinno być pierwsze (photo2)
        self.assertEqual(photos[0], photo2)

    def test_context_contains_photo_form(self):
        """Test że context zawiera photo_form."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        self.assertIn('photo_form', response.context)

    def test_context_contains_emotion_distribution(self):
        """Test że context zawiera emotion_distribution - count per emotional_value (1-5)."""
        # Utwórz emocje z różnymi wartościami
        EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location,
            emotional_value=5, privacy_status='public'
        )
        # Jedna location2 dla user1 żeby zrobić unique constraint
        location2 = Location.objects.create(
            name='Location 2',
            coordinates=Point(18.5, 54.4, srid=4326)
        )
        EmotionPoint.objects.create(
            user=self.user1, location=location2,
            emotional_value=3, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        emotion_distribution = list(response.context['emotion_distribution'])
        # Powinno być: {5: 2 count}
        self.assertTrue(len(emotion_distribution) > 0)
        five_rating = next((item for item in emotion_distribution if item['emotional_value'] == 5), None)
        self.assertIsNotNone(five_rating)
        self.assertEqual(five_rating['count'], 2)

    def test_context_contains_user_emotion_point(self):
        """Test że context zawiera user_emotion_point - czy user już ocenił."""
        # user1 ocenił lokalizację
        user_emotion = EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=4, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        self.assertEqual(response.context['user_emotion_point'], user_emotion)

    def test_context_user_emotion_point_is_none_when_not_rated(self):
        """Test że user_emotion_point to None gdy user nie ocenił."""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        self.assertIsNone(response.context['user_emotion_point'])

    def test_location_annotated_with_avg_emotional_value(self):
        """Test że location ma annotacje: avg_emotional_value."""
        EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location,
            emotional_value=3, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        location = response.context['location']
        self.assertTrue(hasattr(location, 'avg_emotional_value'))
        self.assertEqual(float(location.avg_emotional_value), 4.0)

    def test_location_annotated_with_emotion_points_count(self):
        """Test że location ma annotacje: emotion_points_count."""
        EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location,
            emotional_value=3, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')
        response = self.client.get(self.url)

        location = response.context['location']
        self.assertTrue(hasattr(location, 'emotion_points_count'))
        self.assertEqual(location.emotion_points_count, 2)

    def test_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_nonexistent_location_404(self):
        """Test 404 dla nieistniejącej lokalizacji."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('map:location_detail', kwargs={'pk': 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    # --- POST tests - dodawanie oceny ---

    def test_post_add_new_emotion_rating(self):
        """Test dodania nowej oceny (emotional_value, privacy_status)."""
        self.client.login(username='user1', password='testpass123')

        data = {
            'emotional_value': 5,
            'privacy_status': 'public'
        }
        response = self.client.post(self.url, data)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.url)

        # Sprawdź że utworzono EmotionPoint
        self.assertEqual(EmotionPoint.objects.count(), 1)
        emotion = EmotionPoint.objects.first()
        self.assertEqual(emotion.user, self.user1)
        self.assertEqual(emotion.location, self.location)
        self.assertEqual(emotion.emotional_value, 5)
        self.assertEqual(emotion.privacy_status, 'public')

    def test_post_update_existing_emotion_rating(self):
        """Test aktualizacji istniejącej oceny (update_or_create)."""
        # Utwórz początkową ocenę
        EmotionPoint.objects.create(
            user=self.user1, location=self.location,
            emotional_value=3, privacy_status='public'
        )

        self.client.login(username='user1', password='testpass123')

        data = {
            'emotional_value': 5,
            'privacy_status': 'private'
        }
        response = self.client.post(self.url, data)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)

        # Sprawdź że nie utworzono duplikatu
        self.assertEqual(EmotionPoint.objects.count(), 1)
        emotion = EmotionPoint.objects.first()
        self.assertEqual(emotion.emotional_value, 5)
        self.assertEqual(emotion.privacy_status, 'private')

    def test_post_default_privacy_status_is_public(self):
        """Test że domyślny privacy_status = 'public'."""
        self.client.login(username='user1', password='testpass123')

        data = {
            'emotional_value': 4
            # Brak privacy_status
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)

        emotion = EmotionPoint.objects.first()
        self.assertEqual(emotion.privacy_status, 'public')

    def test_post_success_message_displayed(self):
        """Test że wyświetlany jest success message po dodaniu oceny."""
        self.client.login(username='user1', password='testpass123')

        data = {
            'emotional_value': 5,
            'privacy_status': 'public'
        }
        response = self.client.post(self.url, data, follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('zapisana', str(messages[0]))

    def test_post_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika przy POST."""
        data = {
            'emotional_value': 5,
            'privacy_status': 'public'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    # --- POST tests - dodawanie zdjęcia ---

    def test_post_add_photo_with_caption(self):
        """Test dodania zdjęcia z caption."""
        self.client.login(username='user1', password='testpass123')

        # Utwórz testowy obraz
        image = Image.new('RGB', (100, 100), color='red')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

        data = {
            'image': photo_file,
            'caption': 'Test photo caption'
        }
        response = self.client.post(self.url, data)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.url)

        # Sprawdź że utworzono Photo
        self.assertEqual(Photo.objects.count(), 1)
        photo = Photo.objects.first()
        self.assertEqual(photo.location, self.location)
        self.assertEqual(photo.caption, 'Test photo caption')

    def test_post_add_photo_without_caption(self):
        """Test dodania zdjęcia bez caption (opcjonalny)."""
        self.client.login(username='user1', password='testpass123')

        # Utwórz testowy obraz
        image = Image.new('RGB', (100, 100), color='blue')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

        data = {
            'image': photo_file
            # Brak caption
        }
        response = self.client.post(self.url, data)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)

        # Sprawdź że utworzono Photo
        self.assertEqual(Photo.objects.count(), 1)
        photo = Photo.objects.first()
        self.assertEqual(photo.caption, '')

    def test_post_photo_success_message(self):
        """Test że wyświetlany jest success message po dodaniu zdjęcia."""
        self.client.login(username='user1', password='testpass123')

        # Utwórz testowy obraz
        image = Image.new('RGB', (100, 100), color='green')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

        data = {
            'image': photo_file,
            'caption': 'Test'
        }
        response = self.client.post(self.url, data, follow=True)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('dodane', str(messages[0]))
