# cityfeel/emotions/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import EmotionPoint, Comment, Photo, Report


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
    list_display = ['user', 'location', 'created_at', 'short_content', 'sentiment_badge', 'mismatch_warning']
    list_filter = ['created_at', 'sentiment_label', 'location']
    search_fields = ['user__username', 'content', 'location__name']
    readonly_fields = ['created_at', 'sentiment_score', 'sentiment_label']
    autocomplete_fields = ['user', 'location']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Komentarz', {
            'fields': ('user', 'location', 'content')
        }),
        ('Sentyment', {
            'fields': ('sentiment_score', 'sentiment_label'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = "Treść"

    def sentiment_badge(self, obj):
        colors = {'positive': '#198754', 'neutral': '#6c757d', 'negative': '#dc3545'}
        labels = {'positive': 'Pozytywny', 'neutral': 'Neutralny', 'negative': 'Negatywny'}
        if obj.sentiment_label:
            color = colors.get(obj.sentiment_label, '#6c757d')
            label = labels.get(obj.sentiment_label, obj.sentiment_label)
            score = f" ({obj.sentiment_score:.0f}/5)" if obj.sentiment_score else ""
            return format_html(
                '<span style="color:{};font-weight:bold">{}{}</span>', color, label, score
            )
        return format_html('<span style="color:#aaa">–</span>')
    sentiment_badge.short_description = "Sentyment"

    def mismatch_warning(self, obj):
        if obj.sentiment_score is None or obj.emotion_point_id is None:
            return ""
        try:
            diff = abs(obj.sentiment_score - obj.emotion_point.emotional_value)
            if diff > 1.5:
                return format_html(
                    '<span style="color:#dc3545" title="Sentyment ({}) rozjeżdża się z oceną ({})">&#9888; Niezgodność</span>',
                    obj.sentiment_score, obj.emotion_point.emotional_value
                )
        except Exception:
            pass
        return ""
    mismatch_warning.short_description = "Spójność"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'location', 'emotion_point')


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


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'target_info', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__username', 'description')
    readonly_fields = ('created_at', 'resolved_at', 'resolved_by')
    
    actions = ['mark_as_resolved', 'mark_as_dismissed']

    def target_info(self, obj):
        if obj.location:
            return f"Lokalizacja: {obj.location.name} (ID: {obj.location.id})"
        elif obj.emotion_point:
            return f"Punkt: {obj.emotion_point.id}"
        elif obj.comment:
            return f"Komentarz: {obj.comment.id}"
        return "-"
    target_info.short_description = "Zgłoszony obiekt"

    def mark_as_resolved(self, request, queryset):
        queryset.update(
            status='resolved', 
            resolved_by=request.user, 
            resolved_at=timezone.now()
        )
        self.message_user(request, "Wybrane zgłoszenia zostały oznaczone jako Rozwiązane.")
    mark_as_resolved.short_description = "Oznacz jako Rozwiązane (Akceptacja)"

    def mark_as_dismissed(self, request, queryset):
        queryset.update(
            status='dismissed', 
            resolved_by=request.user, 
            resolved_at=timezone.now()
        )
        self.message_user(request, "Wybrane zgłoszenia zostały odrzucone.")
    mark_as_dismissed.short_description = "Oznacz jako Odrzucone"