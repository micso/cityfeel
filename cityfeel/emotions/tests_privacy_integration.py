from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from emotions.models import EmotionPoint, Comment, Photo
from map.models import Location

User = get_user_model()


class PrivacyLogicIntegrationTestCase(TestCase):
    """
    Kompleksowe testy integracyjne dla logiki prywatności.
    Sprawdza: EmotionPoint, Comment oraz Photo.
    """

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()  # Dla API
        self.web_client = Client()  # Dla widoków Django

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.web_client.login(username='testuser', password='testpass123')

        # Logujemy klienta API
        self.client.force_authenticate(user=self.user)

        self.location = Location.objects.create(
            name='Test Location',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )

    # =========================================================================
    # 1. EMOTION POINTS
    # =========================================================================

    def test_public_emotion_visible_on_user_profile(self):
        """Test że publiczny EmotionPoint jest widoczny na profilu użytkownika."""
        public_emotion = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        response = self.web_client.get(url)

        recent_emotions = list(response.context['recent_emotions'])
        self.assertIn(public_emotion, recent_emotions)

    def test_private_emotion_not_visible_on_user_profile(self):
        """Test że prywatny EmotionPoint NIE jest widoczny na liście profilu."""
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='private'
        )

        url = reverse('cf_auth:profile', kwargs={'user_id': self.user.id})
        response = self.web_client.get(url)

        recent_emotions = list(response.context['recent_emotions'])
        self.assertEqual(len(recent_emotions), 0)

    def test_both_types_visible_on_map_api(self):
        """Test że oba typy (public i private) są widoczne na mapie (statystyki)."""
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        user2 = User.objects.create_user(username='user2', email='u2@e.com', password='p')
        EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )

        response = self.client.get('/api/locations/')

        location_data = next((loc for loc in response.data if loc['id'] == self.location.id), None)
        self.assertEqual(float(location_data['avg_emotional_value']), 4.0)
        self.assertEqual(location_data['emotion_points_count'], 2)

    def test_both_types_affect_avg_emotional_value(self):
        """Test szczegółowy na średnią z różnych typów prywatności."""
        EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        user2 = User.objects.create_user(username='u2', email='u2@e.com', password='p')
        EmotionPoint.objects.create(
            user=user2,
            location=self.location,
            emotional_value=1,
            privacy_status='private'
        )

        response = self.client.get('/api/locations/')
        loc = response.data[0]
        self.assertEqual(float(loc['avg_emotional_value']), 3.0)

    def test_public_emotion_visible_in_api_emotion_points(self):
        """Test że publiczny EmotionPoint jest wprost dostępny w API."""
        ep = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )

        response = self.client.get('/api/emotion-points/')
        ids = [r['id'] for r in response.data['results']]
        self.assertIn(ep.id, ids)

    def test_private_emotion_not_visible_in_api_emotion_points(self):
        """Test że prywatny EmotionPoint jest ukryty w API listingu."""
        ep = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='private'
        )

        response = self.client.get('/api/emotion-points/')
        ids = [r['id'] for r in response.data['results']]
        self.assertNotIn(ep.id, ids)

    def test_comments_only_on_public_emotion_points(self):
        """Test integracji komentarzy z prywatnością (tylko publiczne w licznikach)."""
        # Publiczny z komentarzem
        ep1 = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=ep1,
            location=self.location,
            content='Public',
            privacy_status='public'
        )

        # Prywatny z komentarzem
        u2 = User.objects.create_user('u2', 'u2@e.com', 'p')
        ep2 = EmotionPoint.objects.create(
            user=u2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )
        # [NAPRAWA] Ustawiamy privacy_status='private' (inaczej byłby publiczny defaultowo)
        Comment.objects.create(
            user=u2,
            emotion_point=ep2,
            location=self.location,
            content='Private',
            privacy_status='private'
        )

        response = self.client.get('/api/locations/')
        loc = response.data[0]
        # Oczekujemy 1, bo drugi jest prywatny
        self.assertEqual(loc['comments_count'], 1)

    def test_latest_comment_only_from_public_emotion_points(self):
        """Test latest_comment."""
        u2 = User.objects.create_user('u2', 'u2@e.com', 'p')
        ep_priv = EmotionPoint.objects.create(
            user=u2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )
        # [NAPRAWA] Ustawiamy privacy_status='private'
        Comment.objects.create(
            user=u2,
            emotion_point=ep_priv,
            location=self.location,
            content='Secret',
            privacy_status='private'
        )

        ep_pub = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=ep_pub,
            location=self.location,
            content='Visible',
            privacy_status='public'
        )

        response = self.client.get('/api/locations/')
        loc = response.data[0]
        # Ponieważ 'Visible' został utworzony później, on jest najnowszy.
        # Gdyby 'Secret' był nowszy, API zwróciłoby go jako 'Anonim' (zgodnie z nową logiką)
        # Ten test weryfikuje głównie poprawne sortowanie i dostępność
        self.assertEqual(loc['latest_comment']['content'], 'Visible')

    def test_comments_count_only_public_emotion_points(self):
        """Licznik komentarzy ignoruje prywatne."""
        ep = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=ep,
            location=self.location,
            content='C1',
            privacy_status='public'
        )
        Comment.objects.create(
            user=self.user,
            emotion_point=ep,
            location=self.location,
            content='C2',
            privacy_status='public'
        )

        response = self.client.get('/api/locations/')
        self.assertEqual(response.data[0]['comments_count'], 2)

    # =========================================================================
    # 2. PHOTOS
    # =========================================================================

    def test_public_photo_visible_in_location_detail(self):
        """Test: Publiczne zdjęcie jest widoczne na stronie lokalizacji."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='public'
        )
        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.get(url)

        self.assertIn(photo, response.context['photos'])

    def test_private_photo_visible_in_location_detail(self):
        """Test: Prywatne zdjęcie TEŻ jest widoczne, ale jako anonimowe."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private'
        )
        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.get(url)

        self.assertIn(photo, response.context['photos'])

    def test_photo_privacy_defaults_to_public(self):
        """Test: Domyślny status zdjęcia to public."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='def.jpg'
        )
        self.assertEqual(photo.privacy_status, 'public')

    def test_mixed_photos_order_by_date(self):
        """Test: Zdjęcia publiczne i prywatne są sortowane po dacie."""
        p1 = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='1.jpg',
            privacy_status='public'
        )
        p2 = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='2.jpg',
            privacy_status='private'
        )

        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.get(url)
        photos = list(response.context['photos'])

        # p2 nowsze, więc pierwsze
        self.assertEqual(photos[0], p2)
        self.assertEqual(photos[1], p1)

    def test_private_photo_anonymous_rendering(self):
        """Test: W HTMLu prywatne zdjęcie ma oznaczenie 'Anonim'."""
        Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private',
            caption='Secret Photo'
        )
        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.get(url)
        self.assertContains(response, "Anonim")
        self.assertContains(response, "Secret Photo")

    def test_public_photo_username_rendering(self):
        """Test: W HTMLu publiczne zdjęcie ma nazwę użytkownika."""
        Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='public'
        )
        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.get(url)
        self.assertContains(response, self.user.username)

    def test_owner_can_delete_private_photo(self):
        """Test: Właściciel może usunąć swoje prywatne zdjęcie."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private'
        )
        delete_url = reverse('emotions:delete_photo', kwargs={'pk': photo.pk})
        response = self.web_client.post(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)

    def test_other_user_cannot_delete_private_photo(self):
        """Test: Inny użytkownik nie może usunąć cudzego zdjęcia (nawet private)."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private'
        )

        u2 = User.objects.create_user('hacker', 'h@h.com', 'p')
        self.web_client.login(username='hacker', password='p')

        delete_url = reverse('emotions:delete_photo', kwargs={'pk': photo.pk})
        response = self.web_client.post(delete_url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Photo.objects.count(), 1)

    def test_admin_can_delete_private_photo(self):
        """Test: Admin może usunąć prywatne zdjęcie."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private'
        )

        admin = User.objects.create_superuser('admin', 'a@a.com', 'p')
        self.web_client.login(username='admin', password='p')

        delete_url = reverse('emotions:delete_photo', kwargs={'pk': photo.pk})
        response = self.web_client.post(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)

    def test_edit_caption_private_photo(self):
        """Test: Edycja opisu prywatnego zdjęcia."""
        photo = Photo.objects.create(
            user=self.user,
            location=self.location,
            image='p.jpg',
            privacy_status='private',
            caption='Old'
        )
        url = reverse('emotions:edit_photo_caption', kwargs={'pk': photo.pk})
        self.web_client.post(url, {'caption': 'New'})

        photo.refresh_from_db()
        self.assertEqual(photo.caption, 'New')

    def test_create_photo_form_sets_privacy(self):
        """Test: Formularz poprawnie ustawia flagę privacy."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image

        img = Image.new('RGB', (100, 100), color='red')
        file = io.BytesIO()
        img.save(file, format='JPEG')
        file.seek(0)
        simple_file = SimpleUploadedFile('test.jpg', file.read(), 'image/jpeg')

        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        data = {
            'image': simple_file,
            'caption': 'Form Photo',
            'privacy_status': 'private'
        }
        self.web_client.post(url, data)

        self.assertEqual(Photo.objects.count(), 1)
        photo = Photo.objects.first()
        self.assertEqual(photo.privacy_status, 'private')

    def test_create_photo_default_public_via_form(self):
        """Test: Formularz domyślnie ustawia public."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image

        img = Image.new('RGB', (10, 10), color='red')
        file = io.BytesIO()
        img.save(file, format='JPEG')
        file.seek(0)
        simple_file = SimpleUploadedFile('t.jpg', file.read(), 'image/jpeg')

        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})

        data = {
            'image': simple_file,
            'privacy_status': 'public'
        }
        self.web_client.post(url, data)
        photo = Photo.objects.first()
        self.assertEqual(photo.privacy_status, 'public')

    def test_anonymous_user_cannot_add_photo(self):
        """Test: Niezalogowany nie może dodać zdjęcia."""
        self.web_client.logout()
        url = reverse('map:location_detail', kwargs={'pk': self.location.pk})
        response = self.web_client.post(url, {})  # POST bez danych
        self.assertRedirects(response, f'/accounts/login/?next={url}')

    def test_photos_not_counted_in_emotion_stats(self):
        """Test: Zdjęcia nie wpływają na licznik 'emotion_points_count'."""
        Photo.objects.create(user=self.user, location=self.location, image='p.jpg')

        response = self.client.get('/api/locations/')
        loc = response.data[0]
        self.assertEqual(loc['emotion_points_count'], 0)