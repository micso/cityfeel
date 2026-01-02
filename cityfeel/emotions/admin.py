from django.contrib import admin
from .models import EmotionPoint, Comment  # <--- Doda³em Comment do importu


@admin.register(EmotionPoint)
class EmotionPointAdmin(admin.ModelAdmin):
    """Admin interface for EmotionPoint."""

    list_display = ['user', 'location', 'emotional_value', 'privacy_status', 'created_at']
    list_filter = ['privacy_status', 'emotional_value', 'created_at']
    search_fields = ['user__username', 'location__name']
    readonly_fields = ['created_at', 'updated_at']

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


# --- NOWA SEKCJA DLA KOMENTARZY ---
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin interface for Comment."""
    
    list_display = ['author', 'point', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['created_at']