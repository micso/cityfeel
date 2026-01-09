# ... (UserRegistrationAndProfileFlowTestCase i EmotionPointCreationFlowTestCase bez zmian)

class CommentFlowTestCase(TestCase):
    """Testy E2E dla komentarzy."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='t@e.com', password='pass')
        self.location = Location.objects.create(name='Test Loc', coordinates=Point(18.6, 54.3))
        # Emotion point opcjonalny, komentarz jest do lokalizacji
        EmotionPoint.objects.create(user=self.user, location=self.location, emotional_value=5, privacy_status='public')

    def test_add_comment_visible_in_latest_comment(self):
        """Test: Dodanie komentarza → Widoczny w latest_comment."""
        client = APIClient()
        client.force_authenticate(user=self.user)

        data = {
            'content': 'Test comment content',
            'location_id': self.location.id  # [FIX] location_id zamiast point_id
        }
        response = client.post('/api/comments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = client.get('/api/locations/')
        location_data = next((loc for loc in response.data['results'] if loc['id'] == self.location.id), None)

        self.assertIsNotNone(location_data['latest_comment'])
        self.assertIn('Test comment content', location_data['latest_comment']['content'])
        self.assertEqual(location_data['latest_comment']['username'], 'testuser')