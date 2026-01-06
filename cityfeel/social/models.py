from django.db import models
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ValidationError


class Friendship(models.Model):
    """
    Model reprezentujący relację znajomości lub zaproszenia.
    """
    STATUS_CHOICES = [
        ('pending', 'Oczekujące'),
        ('accepted', 'Zaakceptowane'),
        ('rejected', 'Odrzucone'),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_friendships',
        help_text="Użytkownik wysyłający zaproszenie"
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_friendships',
        help_text="Użytkownik otrzymujący zaproszenie"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Znajomość"
        verbose_name_plural = "Znajomości"
        unique_together = [('creator', 'target')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.creator} -> {self.target} ({self.status})"

    def clean(self):
        """Walidacja modelu (zamiast CheckConstraint w bazie)."""
        if self.creator_id == self.target_id:
            raise ValidationError("Nie możesz wysłać zaproszenia do samego siebie.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def request_exists(cls, user1, user2):
        """Sprawdza czy istnieje już jakakolwiek relacja między użytkownikami."""
        return cls.objects.filter(
            (Q(creator=user1, target=user2) | Q(creator=user2, target=user1)),
            status__in=['pending', 'accepted']
        ).exists()