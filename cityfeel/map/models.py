from django.contrib.gis.db import models


class Location(models.Model):
    """
    CityFeel Location model for storing geographic points.
    Stores location names with geographic coordinates using PostGIS.
    """
    name = models.CharField(
        max_length=200,
        help_text="Nazwa lokalizacji"
    )

    coordinates = models.PointField(
        srid=4326,
        help_text="Współrzędne geograficzne (długość, szerokość)"
    )

    class Meta:
        verbose_name = "Lokalizacja"
        verbose_name_plural = "Lokalizacje"
        db_table = "map_location"
        indexes = [
            models.Index(fields=['name'], name='location_name_idx'),
        ]

    def __str__(self):
        return self.name

    def get_coordinates_display(self):
        return f"Lat: {self.coordinates.y}, Lon: {self.coordinates.x}"
