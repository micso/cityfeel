from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CFUser


@admin.register(CFUser)
class CFUserAdmin(UserAdmin):
    """Admin interface for CFUser with avatar support."""

    # Add avatar to edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('avatar',),
        }),
    )

    # Add avatar to create form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {
            'fields': ('avatar',),
        }),
    )

    # Show avatar status in user list
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'has_avatar']

    def has_avatar(self, obj):
        """Display whether user has avatar."""
        return bool(obj.avatar)

    has_avatar.boolean = True
    has_avatar.short_description = 'Avatar'
