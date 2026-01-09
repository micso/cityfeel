from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point

from auth.models import Friendship
from emotions.models import EmotionPoint
from map.models import Location

User = get_user_model()


class RegisterViewTestCase(TestCase):
    """Testy dla widoku RegisterView."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = Client()
        self.url = reverse('cf_auth:register')

    def test_register_with_valid_data(self):
        """Test rejestracji z poprawnymi danymi."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(self.url, data)

        # Sprawdź redirect po rejestracji
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('map:emotion_map'))

        # Sprawdź że użytkownik został utworzony
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')

    def test_register_auto_login(self):
        """Test auto-logowania po rejestracji."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(self.url, data, follow=True)

        # Sprawdź że użytkownik jest zalogowany
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, 'newuser')

    def test_register_redirect_to_emotion_map(self):
        """Test przekierowania do map:emotion_map po rejestracji."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse('map:emotion_map'))

    def test_register_redirect_if_already_authenticated(self):
        """Test przekierowania już zalogowanego użytkownika."""
        user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )
        self.client.login(username='existinguser', password='testpass123')

        response = self.client.get(self.url)

        # Zalogowany użytkownik powinien być przekierowany
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('map:emotion_map'))

    def test_register_missing_required_fields(self):
        """Test błędu przy braku wymaganych pól."""
        data = {
            'username': 'newuser'
            # Brak email, password1, password2
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)  # Pozostaje na stronie z błędami
        self.assertFormError(response.context['form'], 'email', 'To pole jest wymagane.')
        self.assertFormError(response.context['form'], 'password1', 'To pole jest wymagane.')

    def test_register_mismatched_passwords(self):
        """Test błędu przy niezgodnych hasłach."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass456!'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)

    def test_register_short_password(self):
        """Test błędu przy zbyt krótkim haśle."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'short',
            'password2': 'short'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        # Django waliduje min. 8 znaków
        self.assertIn('password2', response.context['form'].errors)

    def test_register_common_password(self):
        """Test błędu przy zbyt popularnym haśle."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'password',
            'password2': 'password'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)

    def test_register_existing_username(self):
        """Test błędu przy istniejącym username."""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )

        data = {
            'username': 'existinguser',
            'email': 'newemail@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'username', 'Użytkownik o tej nazwie już istnieje.')

    def test_register_invalid_email(self):
        """Test błędu przy nieprawidłowym emailu."""
        data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)

    def test_register_renders_correct_template(self):
        """Test że renderowany jest prawidłowy template."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/register.html')


class UserProfileViewTestCase(TestCase):
    """Testy dla widoku UserProfileView."""

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

        # Lokalizacje
        self.location1 = Location.objects.create(
            name='Location 1',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )
        self.location2 = Location.objects.create(
            name='Location 2',
            coordinates=Point(21.0122, 52.2297, srid=4326)
        )

    def test_view_user_profile(self):
        """Test wyświetlenia profilu użytkownika."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user2.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertEqual(response.context['profile_user'], self.user2)

    def test_profile_context_contains_emotion_statistics(self):
        """Test że context zawiera total_emotions, public_emotions, private_emotions."""
        # Utwórz emocje dla user1
        EmotionPoint.objects.create(
            user=self.user1, location=self.location1,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user1, location=self.location2,
            emotional_value=4, privacy_status='private'
        )

        self.client.login(username='user2', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user1.id})

        response = self.client.get(url)

        self.assertEqual(response.context['total_emotions'], 2)
        self.assertEqual(response.context['public_emotions'], 1)
        self.assertEqual(response.context['private_emotions'], 1)

    def test_profile_recent_public_emotions_limit_10(self):
        """Test że recent_emotions ograniczone do 10, posortowane po -created_at."""
        # Utwórz 15 publicznych emocji
        for i in range(15):
            location = Location.objects.create(
                name=f'Location {i}',
                coordinates=Point(18.0 + i*0.01, 54.0 + i*0.01, srid=4326)
            )
            EmotionPoint.objects.create(
                user=self.user1, location=location,
                emotional_value=5, privacy_status='public'
            )

        self.client.login(username='user2', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user1.id})

        response = self.client.get(url)

        recent_emotions = response.context['recent_emotions']
        self.assertEqual(len(recent_emotions), 10)

    def test_profile_only_public_emotions_visible_to_others(self):
        """Test że prywatne emocje NIE są widoczne w recent_emotions dla innych użytkowników."""
        # Utwórz publiczną i prywatną emocję
        public_emotion = EmotionPoint.objects.create(
            user=self.user1, location=self.location1,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user1, location=self.location2,
            emotional_value=4, privacy_status='private'
        )

        # user2 ogląda profil user1
        self.client.login(username='user2', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user1.id})

        response = self.client.get(url)

        recent_emotions = list(response.context['recent_emotions'])
        self.assertEqual(len(recent_emotions), 1)
        self.assertEqual(recent_emotions[0], public_emotion)

    def test_profile_is_own_profile_flag(self):
        """Test flagi is_own_profile w kontekście."""
        self.client.login(username='user1', password='testpass123')

        # Własny profil
        url_own = reverse('cf_auth:profile', kwargs={'user_id': self.user1.id})
        response_own = self.client.get(url_own)
        self.assertTrue(response_own.context['is_own_profile'])

        # Profil innego użytkownika
        url_other = reverse('cf_auth:profile', kwargs={'user_id': self.user2.id})
        response_other = self.client.get(url_other)
        self.assertFalse(response_other.context['is_own_profile'])

    def test_profile_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        url = reverse('cf_auth:profile', kwargs={'user_id': self.user1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_nonexistent_user_404(self):
        """Test 404 dla nieistniejącego użytkownika."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:profile', kwargs={'user_id': 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class UserProfileEditViewTestCase(TestCase):
    """Testy dla widoku UserProfileEditView."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = Client()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_get_profile_edit_form(self):
        """Test wyświetlenia formularza edycji (GET)."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('cf_auth:profile_edit')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/profile_edit.html')
        self.assertIn('form', response.context)

    def test_edit_profile_success(self):
        """Test edycji własnego profilu (POST)."""
        self.client.login(username='testuser', password='testpass123')
        url = reverse('cf_auth:profile_edit')

        data = {
            'first_name': 'Jan',
            'last_name': 'Kowalski',
            'email': 'jan.kowalski@example.com',
            'description': 'Testowy opis profilu'
        }
        response = self.client.post(url, data)

        # Sprawdź redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('cf_auth:profile', kwargs={'user_id': self.user.id}))

        # Sprawdź zmiany w bazie
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jan')
        self.assertEqual(self.user.last_name, 'Kowalski')
        self.assertEqual(self.user.email, 'jan.kowalski@example.com')
        self.assertEqual(self.user.description, 'Testowy opis profilu')

    def test_edit_profile_always_edits_current_user(self):
        """Test że zawsze edytowany jest profil zalogowanego użytkownika (bezpieczeństwo)."""
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        self.client.login(username='testuser', password='testpass123')
        url = reverse('cf_auth:profile_edit')

        data = {
            'first_name': 'Modified',
            'last_name': 'Name',
            'email': 'modified@example.com',
        }
        response = self.client.post(url, data)

        # Sprawdź że zmieniono testuser, nie user2
        self.user.refresh_from_db()
        user2.refresh_from_db()

        self.assertEqual(self.user.first_name, 'Modified')
        self.assertEqual(user2.first_name, '')  # Nie zmienione

    def test_edit_profile_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        url = reverse('cf_auth:profile_edit')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class CommunityViewTestCase(TestCase):
    """Testy dla widoku CommunityView."""

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
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )

    def test_community_view_list_users(self):
        """Test listy użytkowników z paginacją (10 per page)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/community.html')
        # user1 jest zalogowany, więc nie powinien być na liście
        # user2 i user3 powinni być
        self.assertEqual(len(response.context['users_list']), 2)

    def test_community_excludes_current_user(self):
        """Test że zalogowany użytkownik jest wykluczony z listy."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        user_ids = [user.id for user in users_list]

        self.assertNotIn(self.user1.id, user_ids)
        self.assertIn(self.user2.id, user_ids)
        self.assertIn(self.user3.id, user_ids)

    def test_community_search_by_username(self):
        """Test filtrowania po username (?q=name)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community') + '?q=user2'

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        self.assertEqual(len(users_list), 1)
        self.assertEqual(users_list[0].username, 'user2')

    def test_community_friendship_status_pending_sent(self):
        """Test statusu znajomości pending_sent."""
        # user1 wysłał zaproszenie do user2
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.PENDING
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        user2_obj = next(u for u in users_list if u.id == self.user2.id)

        self.assertEqual(user2_obj.friendship_status, Friendship.PENDING)
        self.assertEqual(user2_obj.friendship_direction, 'sent')

    def test_community_friendship_status_pending_received(self):
        """Test statusu znajomości pending_received."""
        # user2 wysłał zaproszenie do user1
        Friendship.objects.create(
            user=self.user2,
            friend=self.user1,
            status=Friendship.PENDING
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        user2_obj = next(u for u in users_list if u.id == self.user2.id)

        self.assertEqual(user2_obj.friendship_status, Friendship.PENDING)
        self.assertEqual(user2_obj.friendship_direction, 'received')

    def test_community_friendship_status_accepted(self):
        """Test statusu znajomości accepted."""
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        user2_obj = next(u for u in users_list if u.id == self.user2.id)

        self.assertEqual(user2_obj.friendship_status, Friendship.ACCEPTED)

    def test_community_friendship_status_none(self):
        """Test braku znajomości (None)."""
        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:community')

        response = self.client.get(url)

        users_list = list(response.context['users_list'])
        user2_obj = next(u for u in users_list if u.id == self.user2.id)

        self.assertIsNone(user2_obj.friendship_status)

    def test_community_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        url = reverse('cf_auth:community')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


class MyFriendsViewTestCase(TestCase):
    """Testy dla widoku MyFriendsView."""

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
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )

    def test_my_friends_view_accepted_friends(self):
        """Test listy zaakceptowanych znajomych."""
        # user1 ↔ user2 (accepted)
        Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:my_friends')

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/my_friends.html')

        friends_list = response.context['friends_list']
        self.assertEqual(len(friends_list), 1)
        self.assertEqual(friends_list[0].username, 'user2')

    def test_my_friends_view_pending_requests(self):
        """Test listy pending incoming requests."""
        # user2 wysłał zaproszenie do user1
        Friendship.objects.create(
            user=self.user2,
            friend=self.user1,
            status=Friendship.PENDING
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:my_friends')

        response = self.client.get(url)

        pending_requests = response.context['pending_requests']
        self.assertEqual(len(pending_requests), 1)
        self.assertEqual(pending_requests[0].user.username, 'user2')

    def test_my_friends_friendship_id_attached(self):
        """Test że friendship_id jest przypisane do użytkowników."""
        friendship = Friendship.objects.create(
            user=self.user1,
            friend=self.user2,
            status=Friendship.ACCEPTED
        )

        self.client.login(username='user1', password='testpass123')
        url = reverse('cf_auth:my_friends')

        response = self.client.get(url)

        friends_list = response.context['friends_list']
        self.assertEqual(friends_list[0].friendship_id, friendship.id)

    def test_my_friends_unauthenticated_redirect(self):
        """Test przekierowania nieautoryzowanego użytkownika."""
        url = reverse('cf_auth:my_friends')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
