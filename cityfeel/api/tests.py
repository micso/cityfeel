class LocationAPITestCase(TestCase):
    """Testy dla endpointu GET /api/locations/ (Zadanie #35 - Stare Nazwy)"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_authenticate(user=self.user)
        self.url = '/api/locations/'

        # Loc1: 5 (public), 3 (public) -> Avg 4.0
        self.loc1 = Location.objects.create(name='Loc1', coordinates=Point(1, 1))
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=5, privacy_status='public')
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=3, privacy_status='public')

        # Loc2: Brak opinii
        self.loc2 = Location.objects.create(name='Loc2', coordinates=Point(2, 2))

        # Loc3: 4 (public), 1 (private) -> Avg 4.0 (prywatna ignorowana)
        self.loc3 = Location.objects.create(name='Loc3', coordinates=Point(3, 3))
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=4, privacy_status='public')
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=1, privacy_status='private')

    def test_response_fields(self):
        """Sprawdza obecność starych nazw pól."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['results'][0]
        
        self.assertIn('avg_emotional_value', data)
        self.assertIn('emotion_points_count', data)

    def test_average_rating_calculation(self):
        """Sprawdza średnią dla publicznych opinii."""
        response = self.client.get(f'{self.url}{self.loc1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 2)

    def test_private_points_excluded(self):
        """Sprawdza czy prywatne punkty są ignorowane (ZMIANA LOGIKI)."""
        response = self.client.get(f'{self.url}{self.loc3.id}/')
        
        # Oczekujemy 4.0 (tylko publiczna), a nie 2.5 (średnia z obu)
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 1)

    def test_no_opinions(self):
        response = self.client.get(f'{self.url}{self.loc2.id}/')
        self.assertIsNone(response.data['avg_emotional_value'])
        self.assertEqual(response.data['emotion_points_count'], 0)