from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from map.models import Location


class EmotionPoint(models.Model):
    MIN_EMOTIONAL_VALUE = 1
    MAX_EMOTIONAL_VALUE = 5

    PRIVACY_CHOICES = [
        ('public', 'Publiczny'),
        ('private', 'Prywatny'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emotion_points'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='emotion_points'
    )
    emotional_value = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_EMOTIONAL_VALUE),
            MaxValueValidator(MAX_EMOTIONAL_VALUE)
        ]
    )
    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Punkt emocji"
        verbose_name_plural = "Punkty emocji"
        db_table = "emotions_emotion_point"
        unique_together = [('user', 'location')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.location.name} ({self.emotional_value})"


class Comment(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Publiczny'),
        ('private', 'Prywatny'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Autor komentarza"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Lokalizacja, której dotyczy komentarz"
    )
    emotion_point = models.ForeignKey(
        EmotionPoint,
        on_delete=models.CASCADE,
        related_name='related_comments',
        null=True,
        blank=True,
        help_text="Powiązana ocena (jeśli komentarz jest częścią opinii)"
    )
    content = models.TextField(help_text="Treść komentarza")
    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        help_text="Status prywatności komentarza"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Data utworzenia komentarza")

    class Meta:
        verbose_name = "Komentarz"
        verbose_name_plural = "Komentarze"
        db_table = "emotions_comment"
        ordering = ['-created_at']

    def __str__(self):
        return f"Komentarz {self.user} do {self.location.name}"


def validate_image_size(image):
    file_size = image.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Maksymalny rozmiar pliku to {limit_mb}MB")


class Photo(models.Model):
    # [NOWE] Opcje prywatności
    PRIVACY_CHOICES = [
        ('public', 'Publiczny'),
        ('private', 'Prywatny'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='photos',
        help_text="Użytkownik, który dodał zdjęcie",
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='photos',
        help_text="Lokalizacja, której dotyczy zdjęcie"
    )
    image = models.ImageField(
        upload_to='location_photos/%Y/%m/%d/',
        validators=[validate_image_size]
    )
    caption = models.CharField(max_length=255, blank=True)

    # [NOWE] Pole privacy_status
    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        help_text="Status prywatności zdjęcia"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Zdjęcie"
        verbose_name_plural = "Zdjęcia"

    def __str__(self):
        return f"Zdjęcie do lokalizacji {self.location.name}"