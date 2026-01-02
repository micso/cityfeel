from django.contrib.gis.db import models
from django.db.models import Avg

class Location(models.Model):
    """
    CityFeel Location model for storing geographic points.
    Stores location names with geographic coordinates using PostGIS.
    """
    name = models.CharField(
        max_length=200,
        help_text="Name of the location"
    )

    coordinates = models.PointField(
        srid=4326,
        help_text="Geographic coordinates (longitude, latitude)"
    )

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        db_table = "map_location"
        indexes = [
            models.Index(fields=['name'], name='location_name_idx'),
        ]

    def __str__(self):
        return self.name

    def get_coordinates_display(self):
        return f"Lat: {self.coordinates.y}, Lon: {self.coordinates.x}"

    # --- Zadanie #35: Obliczanie œredniej ---
    @property
    def average_rating(self):
        """Calculates average emotional value for this location."""
        # Pobieramy powi¹zane punkty emocji i liczymy œredni¹ z pola 'emotional_value'
        # Wykorzystujemy related_name='emotion_points' z modelu EmotionPoint
        avg = self.emotion_points.aggregate(Avg('emotional_value'))['emotional_value__avg']
        return round(float(avg), 2) if avg is not None else 0.0