from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from emotions.models import EmotionPoint, Comment
from map.models import Location

User = get_user_model()


class CommentAPITestCase(TestCase):
    """Testy dla endpointu POST /api/comments/ - komentarze do emotion points."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        # Użytkownicy testowi
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

        # Publiczny EmotionPoint
        self.public_emotion = EmotionPoint.objects.create(
            user=self.user1,
            location=self.location,
            emotional_value=4,
            privacy_status='public'
        )

        # Prywatny EmotionPoint
        self.private_emotion = EmotionPoint.objects.create(
            user=self.user2,
            location=self.location,
            emotional_value=3,
            privacy_status='private'
        )

        # URL endpointu
        self.url = '/api/comments/'

    # --- POST /api/comments/ - Tworzenie komentarza ---

    def test_create_comment_success(self):
        """Test dodania komentarza do publicznego EmotionPoint (201 CREATED)."""
        self.client.force_authenticate(user=self.user2)

        data = {
            'content': 'Świetne miejsce, polecam!',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź dane odpowiedzi
        self.assertIn('id', response.data)
        self.assertEqual(response.data['content'], 'Świetne miejsce, polecam!')
        self.assertEqual(response.data['username'], 'user2')
        self.assertIn('created_at', response.data)

        # Sprawdź w bazie
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.content, 'Świetne miejsce, polecam!')
        self.assertEqual(comment.user, self.user2)
        self.assertEqual(comment.emotion_point, self.public_emotion)

    def test_create_comment_missing_content(self):
        """Test komentarza z brakującym content (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'point_id': self.public_emotion.id
            # Brak content
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_create_comment_missing_point_id(self):
        """Test komentarza z brakującym point_id (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Test comment'
            # Brak point_id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('point_id', response.data)

    def test_create_comment_nonexistent_emotion_point(self):
        """Test komentarza do nieistniejącego EmotionPoint (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Test comment',
            'point_id': 99999  # Nieistniejący
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('point_id', response.data)

    def test_create_comment_empty_content(self):
        """Test komentarza z pustym content (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': '',  # Pusty string
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_create_comment_whitespace_only_content(self):
        """Test komentarza z samymi spacjami (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': '   ',  # Tylko białe znaki
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_create_comment_unauthenticated(self):
        """Test nieautoryzowanego requesta (401/403)."""
        # NIE autentykuj użytkownika
        data = {
            'content': 'Test comment',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # --- Automatyczne przypisanie użytkownika ---

    def test_user_automatically_assigned(self):
        """Test że user jest automatycznie ustawiony na request.user."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'My comment',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'user1')

        comment = Comment.objects.first()
        self.assertEqual(comment.user, self.user1)

    def test_cannot_override_user_id(self):
        """Test że nie można podmienić user_id w request."""
        self.client.force_authenticate(user=self.user1)

        # Próba podmienienia user poprzez dodanie pola 'user'
        data = {
            'content': 'My comment',
            'point_id': self.public_emotion.id,
            'user': self.user2.id  # Próba podmiany
        }
        response = self.client.post(self.url, data, format='json')

        # Request powinien się udać, ale user powinien być ignorowany
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Komentarz powinien należeć do user1, nie user2
        comment = Comment.objects.first()
        self.assertEqual(comment.user, self.user1)
        self.assertNotEqual(comment.user, self.user2)

    # --- Struktura odpowiedzi ---

    def test_response_structure(self):
        """Test że odpowiedź zawiera wszystkie wymagane pola."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Test comment with all fields',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź obecność wszystkich pól
        required_fields = ['id', 'username', 'content', 'created_at']
        for field in required_fields:
            self.assertIn(field, response.data, f"Brak pola '{field}' w odpowiedzi")

    def test_created_at_format(self):
        """Test poprawności formatu timestamps."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Test timestamp',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('created_at', response.data)
        # created_at powinien być string (ISO format)
        self.assertIsInstance(response.data['created_at'], str)

    # --- Edge cases ---

    def test_create_comment_to_private_emotion_point(self):
        """Test komentarza do prywatnego EmotionPoint (dozwolone w modelu, ale nie w statystykach)."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Comment on private emotion',
            'point_id': self.private_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        # Model dopuszcza komentarze do prywatnych emotion points
        # (choć nie są wyświetlane w statystykach lokalizacji)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        comment = Comment.objects.first()
        self.assertEqual(comment.emotion_point, self.private_emotion)

    def test_multiple_comments_same_user(self):
        """Test że użytkownik może dodać wiele komentarzy do tego samego EmotionPoint."""
        self.client.force_authenticate(user=self.user1)

        # Pierwszy komentarz
        data1 = {
            'content': 'First comment',
            'point_id': self.public_emotion.id
        }
        response1 = self.client.post(self.url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Drugi komentarz
        data2 = {
            'content': 'Second comment',
            'point_id': self.public_emotion.id
        }
        response2 = self.client.post(self.url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Powinny być 2 komentarze
        self.assertEqual(Comment.objects.count(), 2)

    def test_comment_with_special_characters(self):
        """Test komentarza ze znakami specjalnymi i polskimi literami."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'content': 'Świetne miejsce! Polecam każdemu... Ceny: 10-20 zł. Ocena: 5/5 ⭐',
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], data['content'])

        comment = Comment.objects.first()
        self.assertEqual(comment.content, data['content'])

    def test_long_comment_content(self):
        """Test bardzo długiego komentarza (TextField nie ma limitu)."""
        self.client.force_authenticate(user=self.user1)

        long_content = 'A' * 5000  # 5000 znaków
        data = {
            'content': long_content,
            'point_id': self.public_emotion.id
        }
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        comment = Comment.objects.first()
        self.assertEqual(len(comment.content), 5000)