from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from map.models import Location
from emotions.models import EmotionPoint, Comment, Photo

User = get_user_model()

class CityFeelIntegrationTest(TestCase):
    def setUp(self):
        # Tworzymy użytkownika i lokalizację
        self.user = User.objects.create_user(username='tester', password='password123')
        self.location = Location.objects.create(
            name='Rynek Glowny',
            coordinates=Point(19.9367, 50.0614)
        )

    def test_full_location_interaction_scenario(self):
        """
        Scenariusz E2E (#50):
        1. Użytkownik dodaje ocenę (EmotionPoint).
        2. Sprawdzamy czy średnia lokalizacji się aktualizuje (#35).
        3. Użytkownik dodaje komentarz do tej oceny (#31).
        4. Użytkownik dodaje zdjęcie do tej oceny (#40).
        """
        # 1. Dodanie oceny
        emotion = EmotionPoint.objects.create(
            user=self.user, 
            location=self.location, 
            emotional_value=4
        )
        
        # 2. Sprawdzenie średniej (#35)
        self.assertEqual(self.location.average_rating, 4.0)
        
        # 3. Dodanie komentarza (#31)
        # UWAGA: Używamy nazw pól z Twojego modelu: point, author, content
        Comment.objects.create(
            point=emotion, 
            author=self.user, 
            content="Super miejsce!"
        )
        self.assertEqual(emotion.comments.count(), 1)

        # 4. Dodanie zdjęcia (#40)
        # UWAGA: Używamy nazwy pola: point
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x03\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        test_photo = SimpleUploadedFile("test.gif", image_content, content_type="image/gif")
        Photo.objects.create(point=emotion, image=test_photo)
        
        self.assertEqual(emotion.photos.count(), 1)
        print("\n✅ Scenariusz E2E: Ocena, Srednia, Komentarz i Zdjecie sprawdzone pomyslnie!")