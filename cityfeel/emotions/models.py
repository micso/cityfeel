# cityfeel/emotions/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from map.models import Location


class EmotionPoint(models.Model):
    """
    Punkt emocji - pojedynczy wpis emocji użytkownika o lokalizacji w określonym momencie.

    Model jest historyczny: użytkownik może mieć wiele wpisów dla tej samej lokalizacji
    (każdy klik = nowy rekord z własnym created_at). To pozwala na filtr czasowy mapy
    ("jak miasto czuło się w sylwestra") bez utraty danych.

    Agregacje:
    - "Stan bieżący" = średnia z najnowszego wpisu każdego usera per lokalizacja
      (DISTINCT ON (user_id) ORDER BY created_at DESC).
    - "W oknie czasu" = mean-of-means (każdy user dostaje jedną wagę w oknie,
      niezależnie od liczby wpisów).

    Model prywatności:
    - Wszystkie EmotionPoints (publiczne i prywatne) są widoczne na mapie i wpływają na statystyki lokalizacji
    - public: Pokazuje autora (imię i nazwisko, widoczne na profilu użytkownika)
    - private: Anonimowe - nie pokazuje kto je dodał (nie widoczne na profilu użytkownika)
    """
    # Emotional value range constants
    MIN_EMOTIONAL_VALUE = 1
    MAX_EMOTIONAL_VALUE = 5

    PRIVACY_CHOICES = [
        ('public', 'Publiczny'),
        ('private', 'Prywatny'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emotion_points',
        help_text="Użytkownik, który utworzył ten punkt emocji"
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='emotion_points',
        help_text="Lokalizacja powiązana z tą emocją"
    )

    emotional_value = models.PositiveSmallIntegerField(
        db_index= True,
        validators=[
            MinValueValidator(MIN_EMOTIONAL_VALUE),
            MaxValueValidator(MAX_EMOTIONAL_VALUE)
        ],
        help_text=f"Ocena emocjonalna od {MIN_EMOTIONAL_VALUE} (negatywna) do {MAX_EMOTIONAL_VALUE} (pozytywna)"
    )

    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        help_text="Status prywatności: 'public' (z imieniem i nazwiskiem, widoczne na profilu) lub 'private' (anonimowe, nie widoczne na profilu). Wszystkie emocje są widoczne na mapie."
    )

    created_at = models.DateTimeField(
        db_index=True,
        auto_now_add=True,
        help_text="Kiedy ten punkt emocji został utworzony"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Kiedy ten punkt emocji był ostatnio aktualizowany"
    )

    class Meta:
        verbose_name = "Punkt emocji"
        verbose_name_plural = "Punkty emocji"
        db_table = "emotions_emotion_point"
        indexes = [
            models.Index(fields=['user', 'created_at'], name='emotions_user_created_idx'),
            models.Index(fields=['location', 'emotional_value'], name='emotions_loc_value_idx'),
            models.Index(fields=['privacy_status'], name='emotions_privacy_idx'),
            # Wspiera DISTINCT ON (location_id, user_id) ORDER BY ... created_at DESC
            # — agregacja "latest per user at location" w trybie A.
            models.Index(fields=['location', 'user', '-created_at'], name='emotions_loc_user_created_idx'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.location.name} ({self.emotional_value}/{self.MAX_EMOTIONAL_VALUE})"


class Comment(models.Model):
    """
    Komentarz użytkownika do lokalizacji.
    Może być powiązany z oceną (EmotionPoint) lub być samodzielny.
    """
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

    # [WAŻNE] Pole wymagane przez logikę testów i nową architekturę
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

    content = models.TextField(
        help_text="Treść komentarza"
    )

    # [WAŻNE] Pole prywatności komentarza
    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        help_text="Status prywatności komentarza"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Data utworzenia komentarza"
    )

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
    """
    Zdjęcie dodane przez użytkownika do lokalizacji.
    """
    PRIVACY_CHOICES = [
        ('public', 'Publiczny'),
        ('private', 'Prywatny'),
    ]

    # [WAŻNE] Autor zdjęcia (niezbędny dla logiki prywatności)
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

    # [WAŻNE] Status prywatności zdjęcia
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


class Report(models.Model):
    REPORT_REASONS = [
        ('spam', 'Spam lub reklama'),
        ('hate_speech', 'Mowa nienawiści / Nękanie'),
        ('inappropriate', 'Nieodpowiednia treść'),
        ('fake_location', 'Fałszywa lokalizacja'),
        ('other', 'Inne'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'Oczekujące'),
        ('resolved', 'Rozwiązane (Akceptacja)'),
        ('dismissed', 'Odrzucone (Brak naruszeń)'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reports_submitted',
        verbose_name='Zgłaszający'
    )
    
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='reports',
        verbose_name='Zgłoszona Lokalizacja'
    )
    
    emotion_point = models.ForeignKey(
        EmotionPoint, 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='reports',
        verbose_name='Zgłoszony Punkt Emocji'
    )
    
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='reports',
        verbose_name='Zgłoszony Komentarz'
    )

    reason = models.CharField(max_length=20, choices=REPORT_REASONS, verbose_name='Powód')
    description = models.TextField(blank=True, null=True, verbose_name='Dodatkowy opis')
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending', verbose_name='Status')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data zgłoszenia')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Data rozpatrzenia')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='reports_resolved',
        verbose_name='Rozpatrzone przez'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Zgłoszenie'
        verbose_name_plural = 'Zgłoszenia'

    def __str__(self):
        if self.location:
            target = f"Lokalizacja {self.location.id}"
        elif self.emotion_point:
            target = f"Punkt {self.emotion_point.id}"
        elif self.comment:
            target = f"Komentarz {self.comment.id}"
        else:
            target = "Nieznany cel"
        return f"Zgłoszenie {self.id} ({target}) - {self.get_status_display()}"