from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from emotions.models import EmotionPoint, Comment
from map.models import Location

User = get_user_model()

class PrivacyIntegrationTestCase(TestCase):
    """Testy integracyjne prywatności."""

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@e.com', 'pass')
        self.location = Location.objects.create(name='Test', coordinates=Point(0, 0))

    def test_public_comment_visible(self):
        # [FIX] Dodano location=self.location
        Comment.objects.create(
            user=self.user,
            location=self.location,
            content="Public",
            privacy_status='public'
        )
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().privacy_status, 'public')

    def test_private_comment_created(self):
        # [FIX] Dodano location=self.location
        Comment.objects.create(
            user=self.user,
            location=self.location,
            content="Private",
            privacy_status='private'
        )
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().privacy_status, 'private')

    def test_emotion_point_privacy(self):
        ep = EmotionPoint.objects.create(
            user=self.user,
            location=self.location,
            emotional_value=5,
            privacy_status='private'
        )
        self.assertEqual(ep.privacy_status, 'private')