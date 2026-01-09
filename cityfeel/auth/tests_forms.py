from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image

from auth.forms import UserRegistrationForm, UserProfileEditForm

User = get_user_model()


class UserRegistrationFormTestCase(TestCase):
    """Testy dla formularza UserRegistrationForm."""

    def test_valid_form_with_all_required_fields(self):
        """Test poprawnego formularza z wszystkimi wymaganymi polami."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertTrue(form.is_valid())

    def test_missing_username(self):
        """Test braku username (invalid)."""
        form_data = {
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_missing_email(self):
        """Test braku email (invalid)."""
        form_data = {
            'username': 'newuser',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_email(self):
        """Test nieprawidłowego emailu (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'not-an-email',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_missing_password1(self):
        """Test braku password1 (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_missing_password2(self):
        """Test braku password2 (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_mismatched_passwords(self):
        """Test niezgodnych haseł (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass456!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_short_password(self):
        """Test zbyt krótkiego hasła (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'short',
            'password2': 'short'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_common_password(self):
        """Test zbyt popularnego hasła (invalid)."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'password',
            'password2': 'password'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_form_save_creates_user_with_email(self):
        """Test że form.save() tworzy użytkownika z email."""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        }
        form = UserRegistrationForm(data=form_data)

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertTrue(user.check_password('StrongPass123!'))


class UserProfileEditFormTestCase(TestCase):
    """Testy dla formularza UserProfileEditForm."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_valid_form_with_all_fields(self):
        """Test poprawnego formularza z wszystkimi polami."""
        form_data = {
            'first_name': 'Jan',
            'last_name': 'Kowalski',
            'email': 'jan.kowalski@example.com',
            'description': 'Testowy opis profilu'
        }
        form = UserProfileEditForm(data=form_data, instance=self.user)

        self.assertTrue(form.is_valid())

    def test_valid_form_with_only_email(self):
        """Test poprawnego formularza z tylko email (inne opcjonalne)."""
        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(data=form_data, instance=self.user)

        self.assertTrue(form.is_valid())

    def test_clean_email_uniqueness_excludes_self(self):
        """Test walidacji unikalności email (exclude self)."""
        # Inny użytkownik
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

        # testuser może zachować swój własny email
        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(data=form_data, instance=self.user)

        self.assertTrue(form.is_valid())

    def test_clean_email_error_when_taken(self):
        """Test błędu gdy email jest zajęty przez innego użytkownika."""
        # Inny użytkownik z emailem
        other_user = User.objects.create_user(
            username='otheruser',
            email='taken@example.com',
            password='testpass123'
        )

        # testuser próbuje użyć tego samego emaila
        form_data = {
            'email': 'taken@example.com'
        }
        form = UserProfileEditForm(data=form_data, instance=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('Ten adres email jest już używany', str(form.errors['email']))

    def _create_test_image(self, size_mb):
        """Helper do tworzenia testowego obrazu o określonym rozmiarze."""
        # Utwórz obraz w pamięci
        width = height = int((size_mb * 1024 * 1024 / 3) ** 0.5)  # Przybliżony rozmiar
        image = Image.new('RGB', (width, height), color='red')

        # Zapisz do BytesIO
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        return SimpleUploadedFile(
            name='test_avatar.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

    def test_clean_avatar_error_when_too_large(self):
        """Test błędu gdy avatar > 5MB."""
        # Utwórz prawdziwy obraz JPEG większy niż 5MB
        # Duży obraz z wysoką jakością = duży rozmiar
        large_image = Image.new('RGB', (3000, 3000), color='red')
        file = io.BytesIO()
        large_image.save(file, format='JPEG', quality=100)
        file.seek(0)

        # Sprawdź czy mamy > 5MB, jeśli nie, zwiększ rozmiar
        content = file.read()
        if len(content) <= 5242880:
            # Dodaj więcej danych aby przekroczyć 5MB
            content += b'\xff' * (5242881 - len(content))

        large_file = SimpleUploadedFile(
            name='large_avatar.jpg',
            content=content,
            content_type='image/jpeg'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': large_file},
            instance=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('zbyt duży', str(form.errors['avatar']))

    def test_clean_avatar_error_invalid_format_gif(self):
        """Test błędu gdy nieprawidłowy format (.gif)."""
        # Utwórz GIF
        image = Image.new('RGB', (100, 100), color='blue')
        file = io.BytesIO()
        image.save(file, format='GIF')
        file.seek(0)

        gif_file = SimpleUploadedFile(
            name='test_avatar.gif',
            content=file.read(),
            content_type='image/gif'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': gif_file},
            instance=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('Niedozwolony format', str(form.errors['avatar']))

    def test_clean_avatar_error_invalid_format_bmp(self):
        """Test błędu gdy nieprawidłowy format (.bmp)."""
        # Utwórz BMP
        image = Image.new('RGB', (100, 100), color='green')
        file = io.BytesIO()
        image.save(file, format='BMP')
        file.seek(0)

        bmp_file = SimpleUploadedFile(
            name='test_avatar.bmp',
            content=file.read(),
            content_type='image/bmp'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': bmp_file},
            instance=self.user
        )

        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_clean_avatar_ok_for_jpg(self):
        """Test że JPG jest akceptowany."""
        # Utwórz mały JPG
        image = Image.new('RGB', (100, 100), color='red')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        jpg_file = SimpleUploadedFile(
            name='test_avatar.jpg',
            content=file.read(),
            content_type='image/jpeg'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': jpg_file},
            instance=self.user
        )

        self.assertTrue(form.is_valid())

    def test_clean_avatar_ok_for_jpeg(self):
        """Test że JPEG jest akceptowany."""
        # Utwórz mały JPEG
        image = Image.new('RGB', (100, 100), color='blue')
        file = io.BytesIO()
        image.save(file, format='JPEG')
        file.seek(0)

        jpeg_file = SimpleUploadedFile(
            name='test_avatar.jpeg',
            content=file.read(),
            content_type='image/jpeg'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': jpeg_file},
            instance=self.user
        )

        self.assertTrue(form.is_valid())

    def test_clean_avatar_ok_for_png(self):
        """Test że PNG jest akceptowany."""
        # Utwórz mały PNG
        image = Image.new('RGB', (100, 100), color='green')
        file = io.BytesIO()
        image.save(file, format='PNG')
        file.seek(0)

        png_file = SimpleUploadedFile(
            name='test_avatar.png',
            content=file.read(),
            content_type='image/png'
        )

        form_data = {
            'email': 'test@example.com'
        }
        form = UserProfileEditForm(
            data=form_data,
            files={'avatar': png_file},
            instance=self.user
        )

        self.assertTrue(form.is_valid())

    def test_description_max_500_chars(self):
        """Test że description akceptuje do 500 znaków."""
        # 500 znaków - OK
        form_data = {
            'email': 'test@example.com',
            'description': 'A' * 500
        }
        form = UserProfileEditForm(data=form_data, instance=self.user)

        self.assertTrue(form.is_valid())

        # 501 znaków - ERROR
        form_data_long = {
            'email': 'test@example.com',
            'description': 'A' * 501
        }
        form_long = UserProfileEditForm(data=form_data_long, instance=self.user)

        self.assertFalse(form_long.is_valid())
        self.assertIn('description', form_long.errors)
