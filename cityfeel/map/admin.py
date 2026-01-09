from django.contrib.gis import admin
from django.db.models import Avg
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.GISModelAdmin):
    """Admin interface for Location with GIS support and statistics."""
    list_display = ['name', 'get_coordinates_display', 'emotion_count', 'average_emotion']
    search_fields = ['name']
    readonly_fields = ['emotion_count', 'average_emotion', 'coordinates_info']

    fieldsets = (
        ('Lokalizacja', {
            'fields': ('name', 'coordinates')
        }),
        ('Informacje', {
            'fields': ('coordinates_info',),
            'classes': ('collapse',)
        }),
        ('Statystyki', {
            'fields': ('emotion_count', 'average_emotion'),
            'classes': ('collapse',)
        }),
    )

    def coordinates_info(self, obj):
        """Wyświetla współrzędne w czytelnej formie."""
        return f"Lat: {obj.coordinates.y}, Lon: {obj.coordinates.x}"

    coordinates_info.short_description = 'Współrzędne'

    def emotion_count(self, obj):
        """Zwraca liczbę punktów emocji dla lokalizacji."""
        return obj.emotion_points.count()

    emotion_count.short_description = 'Liczba punktów emocji'

    def average_emotion(self, obj):
        """Zwraca średnią ocenę emocjonalną dla lokalizacji."""
        avg = obj.emotion_points.aggregate(Avg('emotional_value'))['emotional_value__avg']
        return round(avg, 2) if avg else 'Brak danych'

    average_emotion.short_description = 'Średnia ocena'

    def get_queryset(self, request):
        """Optimize queries with prefetch_related."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('emotion_points')
