from django.contrib import admin
from django.utils.html import format_html
from .models import EmotionPoint, Comment, Photo


@admin.register(EmotionPoint)
class EmotionPointAdmin(admin.ModelAdmin):
    """Admin interface for EmotionPoint."""

    list_display = ['user', 'location', 'emotional_value', 'privacy_status', 'created_at']
    list_filter = ['privacy_status', 'emotional_value', 'created_at']
    search_fields = ['user__username', 'location__name']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user', 'location']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Emotion Data', {
            'fields': ('user', 'location', 'emotional_value')
        }),
        ('Privacy', {
            'fields': ('privacy_status',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'location')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comment."""
    # [ZMIANA] emotion_point -> location
    list_display = ['user', 'location', 'created_at', 'short_content']
    list_filter = ['created_at', 'user', 'location']
    search_fields = ['user__username', 'content', 'location__name']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'location']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Komentarz', {
            'fields': ('user', 'location', 'content')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def short_content(self, obj):
        """Wyświetla skrót komentarza na liście."""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    short_content.short_description = "Treść"

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'location')


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """Admin interface for Photo."""
    # [ZMIANA] Dodano user do widoków
    list_display = ['location', 'user', 'created_at', 'caption', 'image_preview']
    list_filter = ['created_at', 'location', 'user']
    search_fields = ['location__name', 'caption', 'user__username']
    readonly_fields = ['created_at', 'image_preview']
    autocomplete_fields = ['location', 'user']

    fieldsets = (
        ('Zdjęcie', {
            'fields': ('location', 'user', 'image', 'caption')
        }),
        ('Preview', {
            'fields': ('image_preview',),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        """Wyświetla podgląd zdjęcia."""
        if obj.image:
            return format_html('<img src="{}" width="150" />', obj.image.url)
        return "Brak zdjęcia"

    image_preview.short_description = 'Podgląd'