from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
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
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_initiated'
    )
    friend = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='friendships_received'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'friend'], name='unique_friendship'),
            models.CheckConstraint(check=~Q(user=F('friend')), name='users_cannot_friend_themselves')
        ]

    def __str__(self):
        return f"{self.user} -> {self.friend} ({self.status})"