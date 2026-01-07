from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, F


def user_avatar_upload_path(instance, filename):
    """
    Generate upload path for user avatars.
    Files uploaded to: MEDIA_ROOT/avatars/
    """
    import os
    ext = os.path.splitext(filename)[1].lower()
    new_filename = f"user_{instance.id}_avatar{ext}"
    return f"avatars/{new_filename}"


class CFUser(AbstractUser):
    """
    CityFeel User model extending Django's AbstractUser.
    Adds avatar upload functionality.
    """
    avatar = models.ImageField(
        upload_to=user_avatar_upload_path,
        blank=True,
        null=True,
        help_text="Zdjęcie profilowe użytkownika",
        max_length=500
    )

    description = models.TextField(blank=True, null=True, max_length=500)

    class Meta:
        verbose_name = "Użytkownik"
        verbose_name_plural = "Użytkownicy"
        db_table = "auth_user"

    def __str__(self):
        return self.username

    def get_avatar_url(self):
        """Return avatar URL or None if not set."""
        if self.avatar:
            return self.avatar.url
        return None


class Friendship(models.Model):
    """
    Model reprezentujący relację znajomości między użytkownikami.
    Zadanie #44
    """
    PENDING = 'pending'
    ACCEPTED = 'accepted'

    STATUS_CHOICES = [
        (PENDING, 'Oczekujące'),
        (ACCEPTED, 'Zaakceptowane'),
    ]

    user = models.ForeignKey(
        CFUser,
        on_delete=models.CASCADE,
        related_name='friendships_initiated',
        help_text="Użytkownik wysyłający zaproszenie"
    )
    friend = models.ForeignKey(
        CFUser,
        on_delete=models.CASCADE,
        related_name='friendships_received',
        help_text="Użytkownik otrzymujący zaproszenie"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text="Status relacji (pending/accepted)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Data utworzenia relacji"
    )

    class Meta:
        verbose_name = "Znajomość"
        verbose_name_plural = "Znajomości"
        db_table = "auth_friendship"
        constraints = [
            # UNIQUE(user_id, friend_id)
            models.UniqueConstraint(
                fields=['user', 'friend'],
                name='unique_friendship'
            ),
            # CHECK(user_id != friend_id)
            models.CheckConstraint(
                condition=~Q(user=F('friend')),  # ZMIANA: check -> condition
                name='users_cannot_be_friends_with_themselves'
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.friend} ({self.status})"