from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class HomepageAccessTest(TestCase):
    """Testy dostępu do strony głównej."""

    def setUp(self):
        """Przygotowanie danych testowych."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_logged_in_user_can_access_homepage(self):
        """Test czy zalogowany użytkownik otrzyma status 200 na homepage."""
        # Zaloguj użytkownika
        self.client.login(username='testuser', password='testpass123')

        # Wykonaj request na homepage
        response = self.client.get(reverse('home'))

        # Homepage bezpośrednio ładuje widok mapy bez zmiany URL
        self.assertEqual(response.status_code, 200)
