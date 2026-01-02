from django.contrib.auth.models import AbstractUser
from django.db import models


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
        help_text="User profile picture",
        max_length=500
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "auth_user"

    def __str__(self):
        return self.username

    def get_avatar_url(self):
        """Return avatar URL or None if not set."""
        if self.avatar:
            return self.avatar.url
        return None
