from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.conf import settings

from emotions.models import EmotionPoint
from map.models import Location


class EmotionPointSerializer(serializers.ModelSerializer):
    """
    Serializer dla EmotionPoint z obsługą proximity matching dla Location.

    Request format:
    {
        "latitude": 52.2297,
        "longitude": 21.0122,
        "emotional_value": 4,
        "privacy_status": "public",  # opcjonalne
        "location_name": "Plac Zamkowy"  # opcjonalne - jeśli nie podane, wygeneruje się automatycznie
    }

    Response format:
    {
        "id": 1,
        "latitude": 52.2297,
        "longitude": 21.0122,
        "emotional_value": 4,
        "privacy_status": "public",
        "location_id": 5,
        "location_name": "Plac Zamkowy",  # nazwa podana przez użytkownika lub auto-generowana
        "created_at": "2025-01-03T10:30:00Z",
        "updated_at": "2025-01-03T10:30:00Z",
        "created": true,  # lub "updated": true
    }
    """

    # Pola wejściowe (write-only)
    latitude = serializers.FloatField(
        write_only=True,
        min_value=-90.0,
        max_value=90.0,
        error_messages={
            'min_value': 'Szerokość geograficzna musi być w zakresie -90 do 90.',
            'max_value': 'Szerokość geograficzna musi być w zakresie -90 do 90.',
            'required': 'Pole latitude jest wymagane.',
            'invalid': 'Nieprawidłowy format szerokości geograficznej.',
        }
    )

    longitude = serializers.FloatField(
        write_only=True,
        min_value=-180.0,
        max_value=180.0,
        error_messages={
            'min_value': 'Długość geograficzna musi być w zakresie -180 do 180.',
            'max_value': 'Długość geograficzna musi być w zakresie -180 do 180.',
            'required': 'Pole longitude jest wymagane.',
            'invalid': 'Nieprawidłowy format długości geograficznej.',
        }
    )

    location_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=False,
        help_text="Opcjonalna nazwa lokalizacji. Jeśli nie podana, zostanie wygenerowana automatycznie.",
        error_messages={
            'max_length': 'Nazwa lokalizacji nie może być dłuższa niż 200 znaków.',
            'blank': 'Nazwa lokalizacji nie może być pusta.',
        }
    )

    # Pola wyjściowe (read-only)
    location_id = serializers.IntegerField(source='location.id', read_only=True)
    created = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    class Meta:
        model = EmotionPoint
        fields = [
            'id',
            'latitude',
            'longitude',
            'emotional_value',
            'privacy_status',
            'location_id',
            'location_name',
            'created_at',
            'updated_at',
            'created',
            'updated',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'location_id']
        extra_kwargs = {
            'emotional_value': {
                'error_messages': {
                    'min_value': 'Wartość emocjonalna musi być w zakresie 1-5.',
                    'max_value': 'Wartość emocjonalna musi być w zakresie 1-5.',
                    'required': 'Pole emotional_value jest wymagane.',
                    'invalid': 'Nieprawidłowy format wartości emocjonalnej.',
                }
            },
            'privacy_status': {
                'error_messages': {
                    'invalid_choice': 'Status prywatności musi być "public" lub "private".',
                }
            }
        }

    def get_created(self, obj):
        """Flaga wskazująca czy punkt został utworzony (nie aktualizowany)."""
        return getattr(obj, '_was_created', False)

    def get_updated(self, obj):
        """Flaga wskazująca czy punkt został zaktualizowany (nie utworzony)."""
        return not getattr(obj, '_was_created', False)

    def validate(self, attrs):
        """
        Walidacja na poziomie obiektu.
        Weryfikacja poprawności kombinacji pól.
        """
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')

        # Dodatkowa walidacja współrzędnych (edge cases)
        if latitude is not None and longitude is not None:
            # Sprawdź czy punkt nie jest w środku oceanu (opcjonalna walidacja)
            # Można dodać walidację czy punkt znajduje się w dopuszczalnym obszarze
            pass

        return attrs

    def create(self, validated_data):
        """
        Tworzy lub aktualizuje EmotionPoint z proximity matching dla Location.

        Logika:
        1. Wyciągnij latitude i longitude z validated_data
        2. Znajdź lub utwórz Location używając proximity matching
        3. Sprawdź czy użytkownik ma już EmotionPoint dla tej Location
        4. Jeśli tak - zaktualizuj, jeśli nie - utwórz nowy
        """
        # Wyciągnij współrzędne i opcjonalną nazwę lokalizacji
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        custom_location_name = validated_data.pop('location_name', None)
        user = self.context['request'].user

        # Utwórz punkt PostGIS (longitude FIRST, latitude SECOND - to standard WGS84)
        point = Point(longitude, latitude, srid=4326)

        # Pobierz promień z settings
        proximity_radius_meters = getattr(
            settings,
            'CITYFEEL_LOCATION_PROXIMITY_RADIUS',
            50  # domyślnie 50 metrów
        )

        # Konwertuj metry na stopnie (przybliżenie)
        # 1 stopień szerokości geograficznej ≈ 111320 metrów
        proximity_radius_degrees = proximity_radius_meters / 111320.0

        # Proximity matching: znajdź najbliższą Location w promieniu
        # Używamy dwithin z wartością w stopniach dla SRID 4326
        nearby_location = (
            Location.objects
            .filter(coordinates__dwithin=(point, proximity_radius_degrees))
            .annotate(distance=Distance('coordinates', point))
            .order_by('distance')
            .first()



        )

        if nearby_location:
            # Użyj istniejącej lokalizacji
            location = nearby_location
        else:
            # Utwórz nową lokalizację
            # Użyj nazwy podanej przez użytkownika lub wygeneruj automatycznie
            if custom_location_name:
                location_name = custom_location_name
            else:
                # Nazwa lokalizacji: "Lat: XX.XXXX, Lon: YY.YYYY"
                location_name = f"Lat: {latitude:.4f}, Lon: {longitude:.4f}"

            location = Location.objects.create(
                name=location_name,
                coordinates=point
            )

        # Sprawdź czy użytkownik już ma EmotionPoint dla tej Location
        try:
            emotion_point = EmotionPoint.objects.get(user=user, location=location)

            # Aktualizuj istniejący punkt
            emotion_point.emotional_value = validated_data.get(
                'emotional_value',
                emotion_point.emotional_value
            )
            emotion_point.privacy_status = validated_data.get(
                'privacy_status',
                emotion_point.privacy_status
            )
            emotion_point.save()

            # Oznacz jako zaktualizowany
            emotion_point._was_created = False

        except EmotionPoint.DoesNotExist:
            # Utwórz nowy punkt
            emotion_point = EmotionPoint.objects.create(
                user=user,
                location=location,
                **validated_data
            )

            # Oznacz jako utworzony
            emotion_point._was_created = True

        return emotion_point

    def to_representation(self, instance):
        """
        Dodaj latitude, longitude i location_name do response.
        """
        representation = super().to_representation(instance)

        # Dodaj współrzędne i nazwę z Location
        if instance.location:
            if instance.location.coordinates:
                representation['latitude'] = instance.location.coordinates.y
                representation['longitude'] = instance.location.coordinates.x
            representation['location_name'] = instance.location.name

        return representation
