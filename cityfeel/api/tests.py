from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from emotions.models import EmotionPoint
from map.models import Location

User = get_user_model()

class LocationAPITestCase(TestCase):
    """
    Testy dla endpointu GET /api/locations/ (Zadanie #35).
    Weryfikują: average_rating, total_opinions oraz ignorowanie prywatnych opinii.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_authenticate(user=self.user)
        # Używamy nazwy widoku z routera (locations-list) lub url hardcoded
        self.url = '/api/locations/'

        # Lokalizacja 1: Dwie opinie publiczne (5 i 3) -> Średnia powinna być 4.0
        self.loc1 = Location.objects.create(name='Loc1', coordinates=Point(1, 1, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=5, privacy_status='public')
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=3, privacy_status='public')

        # Lokalizacja 2: Brak opinii -> Średnia None, Liczba 0
        self.loc2 = Location.objects.create(name='Loc2', coordinates=Point(2, 2, srid=4326))

        # Lokalizacja 3: Mieszane (4 publiczna, 1 prywatna) -> Średnia 4.0 (prywatna ignorowana)
        self.loc3 = Location.objects.create(name='Loc3', coordinates=Point(3, 3, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=4, privacy_status='public')
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=1, privacy_status='private')

    def test_list_locations_returns_stats(self):
        """Sprawdza czy lista lokalizacji zawiera pola average_rating i total_opinions."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertTrue(len(results) > 0)
        
        # Sprawdź strukturę pierwszego elementu
        loc_data = results[0]
        self.assertIn('average_rating', loc_data)
        self.assertIn('total_opinions', loc_data)

    def test_average_rating_calculation(self):
        """Sprawdza poprawność obliczeń dla Loc1 (tylko publiczne)."""
        response = self.client.get(f'{self.url}{self.loc1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['average_rating'], 4.0)
        self.assertEqual(response.data['total_opinions'], 2)

    def test_private_opinions_ignored(self):
        """Sprawdza dla Loc3 czy opinia prywatna jest ignorowana."""
        response = self.client.get(f'{self.url}{self.loc3.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Tylko jedna ocena publiczna (4), prywatna (1) nie powinna zaniżać średniej
        self.assertEqual(response.data['average_rating'], 4.0)
        self.assertEqual(response.data['total_opinions'], 1)

    def test_no_opinions_values(self):
        """Sprawdza wartości dla lokalizacji bez opinii."""
        response = self.client.get(f'{self.url}{self.loc2.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIsNone(response.data['average_rating'])
        self.assertEqual(response.data['total_opinions'], 0)