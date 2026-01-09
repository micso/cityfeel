from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from auth.models import Friendship

User = get_user_model()


class FriendshipAPITestCase(TestCase):
    """Testy dla endpointu /api/friendship/ - system znajomych."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        # Utwórz użytkowników testowych
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
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )

        # URL endpointu
        self.url = '/api/friendship/'

    # --- POST /api/friendship/ - Wysyłanie zaproszenia ---

    def test_send_friend_request_success(self):
        """Test wysłania zaproszenia do użytkownika (201 CREATED)."""
        self.client.force_authenticate(user=self.user1)

        data = {'friend_id': self.user2.id}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź dane odpowiedzi
        self.assertIn('id', response.data)
        self.assertEqual(response.data['status'], Friendship.PENDING)
        self.assertEqual(str(response.data['user']), self.user1.username)
        self.assertEqual(str(response.data['friend']), self.user2.username)

        # Sprawdź w bazie
        self.assertEqual(Friendship.objects.count(), 1)
        friendship = Friendship.objects.first()
        self.assertEqual(friendship.user, self.user1)
        self.assertEqual(friendship.friend, self.user2)
        self.assertEqual(friendship.status, Friendship.PENDING)

    def test_send_friend_request_missing_friend_id(self):
        """Test zaproszenia z brakującym friend_id (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {}  # Brak friend_id
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('friend_id', response.data)

    def test_send_friend_request_nonexistent_user(self):
        """Test zaproszenia do nieistniejącego użytkownika (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {'friend_id': 99999}  # Nieistniejący użytkownik
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('friend_id', response.data)

    def test_send_friend_request_to_self(self):
        """Test zaproszenia do samego siebie (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        data = {'friend_id': self.user1.id}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Nie możesz wysłać zaproszenia do samego siebie', str(response.data))

    def test_send_duplicate_friend_request(self):
        """Test duplikatu zaproszenia (400 BAD REQUEST - unique constraint)."""
        self.client.force_authenticate(user=self.user1)

        # Pierwsze zaproszenie
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # Próba wysłania drugiego zaproszenia
        data = {'friend_id': self.user2.id}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('już istnieje', str(response.data))

    def test_send_friend_request_reverse_exists(self):
        """Test zaproszenia gdy istnieje już relacja w drugą stronę (400 BAD REQUEST)."""
        self.client.force_authenticate(user=self.user1)

        # user2 już wysłał zaproszenie do user1
        Friendship.objects.create(
            user=self.user2,
            friend=self.user1,
            status=Friendship.PENDING
        )

        # user1 próbuje wysłać zaproszenie do user2
        data = {'friend_id': self.user2.id}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('już istnieje', str(response.data))

    def test_send_friend_request_unauthenticated(self):
        """Test nieautoryzowanego requesta (401/403)."""
        # NIE autentykuj użytkownika
        data = {'friend_id': self.user2.id}
        response = self.client.post(self.url, data, format='json')

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # --- PATCH /api/friendship/{id}/ - Akceptacja zaproszenia ---

    def test_accept_friend_request_success(self):
        """Test akceptacji zaproszenia przez odbiorcę (200 OK)."""
        # user1 wysyła zaproszenie do user2
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user2 (odbiorca) akceptuje
        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}{friendship.id}/'
        data = {'status': Friendship.ACCEPTED}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Friendship.ACCEPTED)

        # Sprawdź w bazie
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, Friendship.ACCEPTED)

    def test_accept_friend_request_by_sender(self):
        """Test akceptacji zaproszenia przez nadawcę (nadawca też może akceptować)."""
        # user1 wysyła zaproszenie do user2
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user1 (nadawca) akceptuje
        self.client.force_authenticate(user=self.user1)
        url = f'{self.url}{friendship.id}/'
        data = {'status': Friendship.ACCEPTED}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Friendship.ACCEPTED)

    def test_accept_friend_request_by_third_party(self):
        """Test próby akceptacji przez osobę trzecią (403/404)."""
        # user1 wysyła zaproszenie do user2
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user3 (osoba trzecia) próbuje akceptować
        self.client.force_authenticate(user=self.user3)
        url = f'{self.url}{friendship.id}/'
        data = {'status': Friendship.ACCEPTED}
        response = self.client.patch(url, data, format='json')

        # Może być 403 lub 404 w zależności od implementacji get_queryset()
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_patch_nonexistent_friendship(self):
        """Test akceptacji nieistniejącego zaproszenia (404)."""
        self.client.force_authenticate(user=self.user1)

        url = f'{self.url}99999/'
        data = {'status': Friendship.ACCEPTED}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_with_invalid_status(self):
        """Test PATCH z nieprawidłowym statusem (400 BAD REQUEST)."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}{friendship.id}/'
        data = {'status': 'invalid_status'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_already_accepted_friendship(self):
        """Test PATCH zaproszenia już zaakceptowanego (200 OK - no change)."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}{friendship.id}/'
        data = {'status': Friendship.ACCEPTED}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Friendship.ACCEPTED)

    # --- DELETE /api/friendship/{id}/ - Odrzucenie/usunięcie znajomości ---

    def test_delete_pending_request_by_receiver(self):
        """Test odrzucenia zaproszenia przez odbiorcę."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user2 (odbiorca) odrzuca
        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}{friendship.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Sprawdź że usunięto z bazy
        self.assertEqual(Friendship.objects.count(), 0)

    def test_delete_pending_request_by_sender(self):
        """Test cofnięcia zaproszenia przez nadawcę."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user1 (nadawca) cofa zaproszenie
        self.client.force_authenticate(user=self.user1)
        url = f'{self.url}{friendship.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Friendship.objects.count(), 0)

    def test_delete_accepted_friendship(self):
        """Test usunięcia znajomości (status=accepted) przez dowolną stronę."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        # user2 usuwa znajomość
        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}{friendship.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Friendship.objects.count(), 0)

    def test_delete_friendship_by_third_party(self):
        """Test próby usunięcia cudzej relacji (403/404)."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        # user3 (osoba trzecia) próbuje usunąć
        self.client.force_authenticate(user=self.user3)
        url = f'{self.url}{friendship.id}/'
        response = self.client.delete(url)

        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Sprawdź że nie usunięto
        self.assertEqual(Friendship.objects.count(), 1)

    def test_delete_nonexistent_friendship(self):
        """Test usunięcia nieistniejącej relacji (404)."""
        self.client.force_authenticate(user=self.user1)

        url = f'{self.url}99999/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- GET /api/friendship/requests/ - Lista oczekujących zaproszeń ---

    def test_get_pending_requests_list(self):
        """Test pobrania listy otrzymanych zaproszeń (pending)."""
        # user1 wysyła zaproszenie do user2
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )
        # user3 wysyła zaproszenie do user2
        Friendship.objects.create(
            user=self.user3,
            friend=self.user2,
            status=Friendship.PENDING
        )
        # user2 wysyła zaproszenie do user1 (nie powinno być w liście user2)
        Friendship.objects.create(
            user=self.user2,
            friend=self.user1,
            status=Friendship.PENDING
        )

        # user2 sprawdza swoje incoming requests
        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}requests/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Tylko 2 incoming (od user1 i user3)

        # Sprawdź że są to odpowiednie requesty
        usernames = {item['user'] for item in response.data}
        self.assertEqual(usernames, {'user1', 'user3'})

    def test_get_pending_requests_empty_list(self):
        """Test pustej listy gdy brak zaproszeń."""
        self.client.force_authenticate(user=self.user1)
        url = f'{self.url}requests/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_pending_requests_filters_accepted(self):
        """Test filtrowania - tylko pending (nie accepted)."""
        # user1 wysyła pending do user2
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )
        # user3 wysłał i user2 zaakceptował (nie powinno być na liście)
        Friendship.objects.create(
            user=self.user3,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}requests/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Tylko pending
        self.assertEqual(response.data[0]['status'], Friendship.PENDING)

    def test_get_pending_requests_sorted_by_created_at_desc(self):
        """Test sortowania po created_at DESC."""
        # Utwórz zaproszenia w kolejności
        f1 = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )
        f2 = Friendship.objects.create(
            user=self.user3,
            friend=self.user2,
            status=Friendship.PENDING
        )

        self.client.force_authenticate(user=self.user2)
        url = f'{self.url}requests/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Najnowsze powinno być pierwsze (f2)
        self.assertEqual(response.data[0]['user'], 'user3')
        self.assertEqual(response.data[1]['user'], 'user1')

    def test_get_pending_requests_unauthenticated(self):
        """Test nieautoryzowanego requesta (401/403)."""
        url = f'{self.url}requests/'
        response = self.client.get(url)

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # --- GET /api/friends/ - Lista znajomych ---

    def test_get_friends_list(self):
        """Test pobrania listy znajomych (status=accepted)."""
        # user1 ↔ user2 (zaakceptowana)
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )
        # user1 ↔ user3 (pending - nie powinno być na liście)
        Friendship.objects.create(
            user=self.user1,
            friend=self.user3,
            status=Friendship.PENDING
        )

        self.client.force_authenticate(user=self.user1)
        url = '/api/friends/'  # Alias endpoint
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Tylko zaakceptowany (user2)
        self.assertEqual(response.data[0]['username'], 'user2')

    def test_get_friends_empty_list(self):
        """Test pustej listy gdy brak znajomych."""
        self.client.force_authenticate(user=self.user1)
        url = '/api/friends/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_friends_bidirectional(self):
        """Test że lista zawiera znajomych z obu kierunków relacji."""
        # user2 → user1 (user1 widzi user2)
        Friendship.objects.create(
            user=self.user2,
            friend=self.user1,
            status=Friendship.ACCEPTED
        )
        # user1 → user3 (user1 widzi user3)
        Friendship.objects.create(
            user=self.user1,
            friend=self.user3,
            status=Friendship.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = '/api/friends/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        usernames = {friend['username'] for friend in response.data}
        self.assertEqual(usernames, {'user2', 'user3'})

    def test_get_friends_response_structure(self):
        """Test struktury odpowiedzi (friendship_id, friendship_since)."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.force_authenticate(user=self.user1)
        url = '/api/friends/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        friend_data = response.data[0]
        required_fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'friendship_id', 'friendship_since']
        for field in required_fields:
            self.assertIn(field, friend_data)

        self.assertEqual(friend_data['friendship_id'], friendship.id)

    def test_get_friends_unauthenticated(self):
        """Test nieautoryzowanego requesta (401/403)."""
        url = '/api/friends/'
        response = self.client.get(url)

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    # --- Edge cases ---

    def test_user_deletion_deletes_friendships(self):
        """Test że usunięcie użytkownika usuwa friendship (cascade)."""
        # user1 ↔ user2
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        # Usuń user1
        self.user1.delete()

        # Sprawdź że friendship też został usunięty
        self.assertEqual(Friendship.objects.count(), 0)

    def test_retrieve_friendship_detail(self):
        """Test GET /api/friendship/{id}/ - retrieve single friendship."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        self.client.force_authenticate(user=self.user1)
        url = f'{self.url}{friendship.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], friendship.id)
        self.assertEqual(response.data['status'], Friendship.PENDING)
