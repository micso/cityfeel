from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CFUser, Friendship


@admin.register(CFUser)
class CFUserAdmin(UserAdmin):
    """Admin interface for CFUser with avatar support."""

    # Add avatar to edit form
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('avatar', 'description'),
        }),
    )

    # Add avatar to create form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {
            'fields': ('avatar', 'description'),
        }),
    )

    # Show avatar status in user list
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'has_avatar']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    date_hierarchy = 'date_joined'

    def has_avatar(self, obj):
        """Display whether user has avatar."""
        return bool(obj.avatar)

    has_avatar.boolean = True
    has_avatar.short_description = 'Avatar'


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    """Admin interface for Friendship model."""
    list_display = ['user', 'friend', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'friend__username']
    autocomplete_fields = ['user', 'friend']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Relacja', {
            'fields': ('user', 'friend', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'friend')