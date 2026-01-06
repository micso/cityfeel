from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=255)
    # Dodajemy nowe pole address
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    # Zakładam, że masz te pola do ocen, bo były w serializerze
    average_rating = models.FloatField(default=0.0)
    ratings_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name