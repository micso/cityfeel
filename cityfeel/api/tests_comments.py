from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

# Importujemy modele z emotions oraz Location z map
from emotions.models import EmotionPoint, Comment
from map.models import Location  # Zakładam, że model Location jest w aplikacji map

User = get_user_model()


class CommentTestCase(APITestCase):
    def setUp(self):
        # 1. Tworzymy użytkowników
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com',
                                                        password='password123')

        # 2. Tworzymy Lokalizację (jest wymagana przez EmotionPoint i Comment)
        # Tworzymy generyczną lokalizację. Jeśli Twój model Location wymaga lat/lng,
        # Django zazwyczaj pozwala na ich domyślne wartości lub nulle w testach,
        # ale podaję przykładowe dane.
        self.location = Location.objects.create(
            name="Test Location",
            # Jeśli Location wymaga współrzędnych, odkomentuj poniższe:
            # latitude=52.2297,
            # longitude=21.0122
        )

        # 3. Tworzymy EmotionPoint (zgodnie z Twoim modelem)
        self.emotion_point = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,  # Wartość 1-5
            privacy_status='public'
        )

        # 4. Tworzymy komentarz
        # Twój model Comment wymaga 'location' i opcjonalnie 'emotion_point'
        self.comment = Comment.objects.create(
            user=self.user,
            location=self.location,
            emotion_point=self.emotion_point,
            content="This is a test comment",  # Pole nazywa się 'content', nie 'text'
            privacy_status='public'
        )

        # 5. URL-e
        # Zakładam standardowe nazewnictwo routera.
        self.list_url = reverse('comment-list')
        self.detail_url = reverse('comment-detail', args=[self.comment.id])

    # --- Testy pobierania (GET) ---

    def test_get_comments_list(self):
        """1. Test pobierania listy komentarzy."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Sprawdzamy czy w odpowiedzi są dane
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_comment_detail(self):
        """2. Test pobierania szczegółów komentarza."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Pole w API to prawdopodobnie 'content' (zgodnie z modelem)
        self.assertEqual(response.data['content'], "This is a test comment")

    def test_get_comment_not_found(self):
        """3. Test pobierania nieistniejącego komentarza."""
        url = reverse('comment-detail', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Testy tworzenia (POST) ---

    def test_create_comment_authenticated(self):
        """4. Użytkownik zalogowany może dodać komentarz."""
        self.client.force_authenticate(user=self.user)
        # Przy tworzeniu komentarza musimy podać ID lokalizacji i treść
        data = {
            "location": self.location.id,
            "emotion_point": self.emotion_point.id,  # Opcjonalne powiązanie
            "content": "New comment content"
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 2)

    def test_create_comment_unauthenticated(self):
        """5. Niezalogowany użytkownik NIE może dodać komentarza."""
        data = {
            "location": self.location.id,
            "content": "Anonymous comment"
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_comment_invalid_data(self):
        """6. Próba utworzenia pustego komentarza."""
        self.client.force_authenticate(user=self.user)
        data = {
            "location": self.location.id,
            "content": ""  # Pusty tekst
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_comment_no_location(self):
        """7. Próba utworzenia komentarza bez lokalizacji (wymagane pole)."""
        self.client.force_authenticate(user=self.user)
        data = {
            "content": "Orphan comment"
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Testy edycji (PUT/PATCH) ---

    def test_update_comment_owner(self):
        """8. Właściciel może edytować swój komentarz."""
        self.client.force_authenticate(user=self.user)
        data = {"content": "Updated content"}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Updated content")

    def test_update_comment_not_owner(self):
        """9. Inny użytkownik NIE może edytować cudzego komentarza."""
        self.client.force_authenticate(user=self.other_user)
        data = {"content": "Hacked content"}
        response = self.client.patch(self.detail_url, data)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_update_comment_unauthenticated(self):
        """10. Niezalogowany nie może edytować."""
        data = {"content": "Anon update"}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_comment_invalid(self):
        """11. Próba ustawienia pustego tekstu podczas edycji."""
        self.client.force_authenticate(user=self.user)
        data = {"content": ""}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Testy usuwania (DELETE) ---

    def test_delete_comment_owner(self):
        """12. Właściciel może usunąć swój komentarz."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

    def test_delete_comment_not_owner(self):
        """13. Inny użytkownik NIE może usunąć cudzego komentarza."""
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.detail_url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_delete_comment_unauthenticated(self):
        """14. Niezalogowany nie może usunąć."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_comment_admin(self):
        """15. Admin może usunąć dowolny komentarz."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_comment_str_representation(self):
        """16. Test metody __str__ modelu."""
        expected_str = f"Komentarz {self.user} do {self.location.name}"
        self.assertEqual(str(self.comment), expected_str)