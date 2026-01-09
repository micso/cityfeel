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

    def test_validate_image_size_success(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        validate_image_size(photo_file)

    def test_validate_image_size_too_large(self):
        large_content = b'X' * (5 * 1024 * 1024 + 1)
        large_file = SimpleUploadedFile('large.jpg', large_content, 'image/jpeg')
        with self.assertRaises(ValidationError):
            validate_image_size(large_file)

    def test_upload_path_pattern(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        photo = Photo.objects.create(location=self.location, image=photo_file, privacy_status='public')
        self.assertIn('location_photos/', photo.image.name)

    def test_relation_with_location(self):
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        photo = Photo.objects.create(location=self.location, image=photo_file, privacy_status='public')
        self.assertEqual(photo.location, self.location)

    def test_ordering_by_created_at_desc(self):
        img = self._create_test_image()
        p1 = Photo.objects.create(location=self.location, image=SimpleUploadedFile('1.jpg', img.read(), 'image/jpeg'), privacy_status='public')
        img.seek(0)
        p2 = Photo.objects.create(location=self.location, image=SimpleUploadedFile('2.jpg', img.read(), 'image/jpeg'), privacy_status='public')
        photos = list(Photo.objects.all().order_by('-created_at'))
        self.assertEqual(photos[0].id, p2.id)

    def test_photo_str_method(self):
        img = self._create_test_image()
        photo = Photo.objects.create(location=self.location, image=SimpleUploadedFile('t.jpg', img.read(), 'image/jpeg'), privacy_status='public')
        self.assertTrue(str(photo).startswith("Zdjęcie do lokalizacji"))


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
        image_file = self._create_test_image()
        photo_file = SimpleUploadedFile('test.jpg', image_file.read(), 'image/jpeg')
        form_long = PhotoForm(data={'caption': 'A'*256, 'privacy_status': 'public'}, files={'image': photo_file})
        self.assertFalse(form_long.is_valid())