from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.gis.geos import Point
import io
from PIL import Image
from datetime import datetime

from emotions.models import Photo, validate_image_size
from emotions.forms import PhotoForm
from map.models import Location

"""Testy dla modelu Photo."""


class PhotoModelTestCase(TestCase):
    def setUp(self):
        self.location = Location.objects.create(name='Test', coordinates=Point(18.6, 54.3))

    def _create_test_image(self):
        image = Image.new('RGB', (100, 100), color='red')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)
        return file

    def test_create_photo_with_image_and_caption(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        photo = Photo.objects.create(
            location=self.location, image=photo_file, caption='Capt', privacy_status='public'
        )
        self.assertEqual(photo.caption, 'Capt')

    def test_create_photo_without_caption(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        photo = Photo.objects.create(
            location=self.location, image=photo_file, privacy_status='public'
        )
        self.assertEqual(photo.caption, '')
        self.assertEqual(photo.location, self.location)
        self.assertEqual(photo.caption, 'Test caption')
        self.assertIsNotNone(photo.image)
        self.assertIsNotNone(photo.created_at)
        self.assertIsNotNone(photo.image)

    def test_validate_image_size_success(self):
        """Test walidacji validate_image_size - obraz poniżej 5MB (OK)."""
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        # Nie powinno rzucić wyjątku
        try:
            validate_image_size(photo_file)
        except ValidationError:
            self.fail("validate_image_size() raised ValidationError unexpectedly!")

    def test_validate_image_size_too_large(self):
        """Test walidacji validate_image_size - obraz powyżej 5MB (ERROR)."""
        # Utwórz plik większy niż 5MB
        large_content = b'X' * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
        large_file = SimpleUploadedFile(
            name='large_photo.jpg',
            content=large_content,
            content_type='image/jpeg'
        )

        with self.assertRaises(ValidationError) as context:
            validate_image_size(large_file)

    def test_upload_path_pattern(self):
        """Test ścieżki upload: location_photos/%Y/%m/%d/."""
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        photo = Photo.objects.create(
            location=self.location,
            image=photo_file
        )

        # Sprawdź czy ścieżka zawiera location_photos/%Y/%m/%d/
        self.assertIn('location_photos/', photo.image.name)

        # Sprawdź format daty w ścieżce (YYYY/MM/DD)
        today = datetime.now()
        year_month_day = f"{today.year}/{today.month:02d}/{today.day:02d}"
        self.assertIn(year_month_day, photo.image.name)

    def test_relation_with_location(self):
        """Test relacji z Location (ForeignKey, related_name='photos')."""
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        photo = Photo.objects.create(
            location=self.location,
            image=photo_file
        )

        # Test ForeignKey
        self.assertEqual(photo.location, self.location)

        # Test related_name
        self.assertIn(photo, self.location.photos.all())
        self.assertEqual(self.location.photos.count(), 1)

    def test_ordering_by_created_at_desc(self):
        """Test ordering by -created_at (używane w widokach)."""
        image_file1 = self._create_test_image()
        photo_file1 = SimpleUploadedFile(
            name='photo1.jpg',
            content=image_file1.read(),
            content_type='image/jpeg'
        )
        photo1 = Photo.objects.create(
            location=self.location,
            image=photo_file1
        )

        image_file2 = self._create_test_image()
        photo_file2 = SimpleUploadedFile(
            name='photo2.jpg',
            content=image_file2.read(),
            content_type='image/jpeg'
        )
        photo2 = Photo.objects.create(
            location=self.location,
            image=photo_file2
        )

        # Pobierz z explicit ordering (jak w widokach)
        photos = list(Photo.objects.all().order_by('-created_at'))

        # Najnowsze powinno być pierwsze (photo2) - porównaj ID
        self.assertEqual(photos[0].id, photo2.id)
        self.assertEqual(photos[1].id, photo1.id)

    def test_photo_str_method(self):
        """Test metody __str__()."""
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        photo = Photo.objects.create(
            location=self.location,
            image=photo_file
        )

        expected_str = f"Zdjęcie do lokalizacji {self.location.name}"
        self.assertEqual(str(photo), expected_str)

class PhotoFormTestCase(TestCase):
    def setUp(self):
        self.location = Location.objects.create(name='Test', coordinates=Point(18.6, 54.3))

    def _create_test_image(self):
        image = Image.new('RGB', (100, 100), color='blue')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)
        return file

    def test_valid_form_with_image_and_caption(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        form = PhotoForm(data={'caption': 'Capt', 'privacy_status': 'public'}, files={'image': photo_file})
        self.assertTrue(form.is_valid())

    def test_valid_form_with_image_no_caption(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        form = PhotoForm(data={'privacy_status': 'public'}, files={'image': photo_file})
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_image(self):
        form = PhotoForm(data={'caption': 'Capt', 'privacy_status': 'public'}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_form_caption_max_255_chars(self):
        """Test że caption akceptuje do 255 znaków."""
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile(
            name='test_photo.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        # 255 znaków - OK
        form_ok = PhotoForm(
            data={'caption': 'A' * 255},
            files={'image': photo_file}
        )
        self.assertTrue(form_ok.is_valid())

        # 256 znaków - ERROR
        image_file2 = self._create_test_image()
        photo_file2 = SimpleUploadedFile(
            name='test_photo2.jpg',
            content=image_file2.read(),
            content_type='image/jpeg'
        )

        form_long = PhotoForm(
            data={'caption': 'A' * 256},
            files={'image': photo_file2}
        )
        self.assertFalse(form_long.is_valid())
        self.assertIn('caption', form_long.errors)

        def test_form_has_bootstrap_classes(self):
            """Test że form ma Bootstrap classes na widgets."""
            form = PhotoForm()

            # Sprawdź widgets
            self.assertIn('form-control', form.fields['caption'].widget.attrs['class'])
            self.assertIn('form-control', form.fields['image'].widget.attrs['class'])

