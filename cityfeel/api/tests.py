from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from map.models import Location
from emotions.models import EmotionPoint

User = get_user_model()

class LocationAPITestCase(TestCase):
    """
    Tests for GET /api/locations/ (Task #35).
    Checks average_rating and total_opinions calculation.
    """

    def setUp(self):
        self.client = APIClient()
        # Utworz dwoch uzytkownikow, aby moc dodac wiecej niz 1 opinie do lokalizacji
        self.user = User.objects.create_user(username='testuser', password='password')
        self.user2 = User.objects.create_user(username='testuser2', password='password')
        
        self.client.force_authenticate(user=self.user)
        self.url = '/api/locations/'

        # Location 1: 5 (public), 3 (public) -> Avg 4.0
        self.loc1 = Location.objects.create(name='Loc1', coordinates=Point(1, 1, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=5, privacy_status='public')
        EmotionPoint.objects.create(user=self.user2, location=self.loc1, emotional_value=3, privacy_status='public') # Drugi uzytkownik

        # Location 2: No opinions
        self.loc2 = Location.objects.create(name='Loc2', coordinates=Point(2, 2, srid=4326))

        # Location 3: 4 (public), 1 (private) -> Avg 4.0 (private excluded)
        self.loc3 = Location.objects.create(name='Loc3', coordinates=Point(3, 3, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=4, privacy_status='public')
        EmotionPoint.objects.create(user=self.user2, location=self.loc3, emotional_value=1, privacy_status='private') # Drugi uzytkownik

    def test_list_locations_returns_stats(self):
        """Sprawdza czy lista lokalizacji zawiera pola average_rating i total_opinions."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Sprawdzamy pierwszy element
        data = response.data['results'][0]
        
        # Uzywamy starych nazw pol (zgodnie z ustaleniami)
        self.assertIn('avg_emotional_value', data)
        self.assertIn('emotion_points_count', data)

    def test_average_rating_calculation(self):
        """Sprawdza poprawnosc obliczen dla Loc1 (tylko publiczne)."""
        response = self.client.get(f'{self.url}{self.loc1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # (5 + 3) / 2 = 4.0
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 2)

    def test_private_opinions_ignored(self):
        """Sprawdza dla Loc3 czy opinia prywatna jest ignorowana."""
        response = self.client.get(f'{self.url}{self.loc3.id}/')
        
        # Oczekujemy 4.0 (tylko publiczna), a nie 2.5 (srednia z obu)
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 1)

    def test_no_opinions_values(self):
        """Sprawdza wartosci dla lokalizacji bez opinii."""
        response = self.client.get(f'{self.url}{self.loc2.id}/')
        
        self.assertIsNone(response.data['avg_emotional_value'])
        self.assertEqual(response.data['emotion_points_count'], 0)