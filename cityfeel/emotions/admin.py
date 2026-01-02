from django.contrib import admin
from .models import EmotionPoint, Comment, Photo

# --- WIDOKI ZAGNIE¯D¯ONE (INLINES) ---
# Pozwalaj¹ widzieæ komentarze i zdjêcia bezpoœrednio w edycji punktu

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1  # Puste miejsce na dodanie 1 nowego komentarza od razu
    readonly_fields = ['created_at']

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1  # Puste miejsce na dodanie 1 nowego zdjêcia
    readonly_fields = ['created_at']


# --- G£ÓWNE KONFIGURACJE ---

@admin.register(EmotionPoint)
class EmotionPointAdmin(admin.ModelAdmin):
    """Admin interface for EmotionPoint."""
    list_display = ['user', 'location', 'emotional_value', 'privacy_status', 'created_at']
    list_filter = ['privacy_status', 'emotional_value', 'created_at']
    search_fields = ['user__username', 'location__name']
    readonly_fields = ['created_at', 'updated_at']

    # Tutaj podpinamy "Inlines" - czyli widok dzieci (komentarze i zdjêcia)
    inlines = [CommentInline, PhotoInline]

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
        return super().get_queryset(request).select_related('user', 'location')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'point', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['created_at']


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['point', 'created_at', 'caption']
    list_filter = ['created_at']
    search_fields = ['caption', 'point__location__name']
    readonly_fields = ['created_at']