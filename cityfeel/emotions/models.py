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
        ('public', 'Public'),
        ('private', 'Private'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emotion_points',
        help_text="User who created this emotion point"
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='emotion_points',
        help_text="Location associated with this emotion"
    )

    emotional_value = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_EMOTIONAL_VALUE),
            MaxValueValidator(MAX_EMOTIONAL_VALUE)
        ],
        help_text=f"Emotional rating from {MIN_EMOTIONAL_VALUE} (negative) to {MAX_EMOTIONAL_VALUE} (positive)"
    )

    privacy_status = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public',
        help_text="Visibility of this emotion point"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this emotion point was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this emotion point was last updated"
    )

    class Meta:
        verbose_name = "Emotion Point"
        verbose_name_plural = "Emotion Points"
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
