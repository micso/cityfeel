from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from map.models import Location


class EmotionPoint(models.Model):
    """
    User emotional feedback about a location.
    Represents how users feel about specific city locations.
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
        help_text="Widoczność tego punktu emocji"
    )

    created_at = models.DateTimeField(
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
        unique_together = [('user', 'location')]
        indexes = [
            models.Index(fields=['user', 'created_at'], name='emotions_user_created_idx'),
            models.Index(fields=['location', 'emotional_value'], name='emotions_loc_value_idx'),
            models.Index(fields=['privacy_status'], name='emotions_privacy_idx'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.location.name} ({self.emotional_value}/{self.MAX_EMOTIONAL_VALUE})"


# --- Nowy kod dla Zadania #31 (jako osobna klasa) ---

class Comment(models.Model):
    """
    Komentarz użytkownika do punktu emocji.
    Zadanie #31
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_comments',
        help_text="Autor komentarza"
    )
    emotion_point = models.ForeignKey(
        EmotionPoint,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Punkt emocji, którego dotyczy komentarz"
    )
    content = models.TextField(
        help_text="Treść komentarza"
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
        return f"Komentarz użytkownika {self.user} do punktu {self.emotion_point_id}"