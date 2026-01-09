from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from emotions.models import EmotionPoint, Comment, Photo
from map.models import Location

User = get_user_model()

class DeleteEmotionViewTestCase(TestCase):
    """Testy usuwania (widoki)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('u1', 'e@e.com', 'pass')
        self.location = Location.objects.create(name='Loc', coordinates=Point(0,0))
        self.emotion = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=5
        )
        # [FIX] Poprawna nazwa URL: delete_emotion
        self.url = reverse('emotions:delete_emotion', kwargs={'pk': self.emotion.pk})

    def test_delete_own_emotion(self):
        self.client.login(username='u1', password='pass')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EmotionPoint.objects.count(), 0)

    def test_delete_other_user_emotion_forbidden(self):
        u2 = User.objects.create_user('u2', 'e2@e.com', 'pass')
        self.client.login(username='u2', password='pass')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(EmotionPoint.objects.count(), 1)


class DeleteCommentViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('u1', 'e@e.com', 'pass')
        self.location = Location.objects.create(name='Loc', coordinates=Point(0,0))
        self.comment = Comment.objects.create(
            user=self.user, location=self.location, content="Test"
        )
        # [FIX] Poprawna nazwa URL: delete_comment
        self.url = reverse('emotions:delete_comment', kwargs={'pk': self.comment.pk})

    def test_delete_own_comment(self):
        self.client.login(username='u1', password='pass')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)


class DeletePhotoViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('u1', 'e@e.com', 'pass')
        self.location = Location.objects.create(name='Loc', coordinates=Point(0,0))
        self.photo = Photo.objects.create(
            user=self.user, location=self.location, image="t.jpg", privacy_status='public'
        )
        # [FIX] Poprawna nazwa URL: delete_photo
        self.url = reverse('emotions:delete_photo', kwargs={'pk': self.photo.pk})

    def test_delete_own_photo(self):
        self.client.login(username='u1', password='pass')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Photo.objects.count(), 0)