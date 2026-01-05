from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.conf import settings
from drf_spectacular.utils import extend_schema_field

from emotions.models import EmotionPoint
from map.models import Location


@extend_schema_field({
    'type': 'object',
    'properties': {
        'latitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -90.0,
            'maximum': 90.0,
            'description': 'Szerokosc geograficzna'
        },
        'longitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -180.0,
            'maximum': 180.0,
            'description': 'Dlugosc geograficzna'
        }
    },
    'required': ['latitude', 'longitude'],
    'example': {
        'latitude': 54.3520,
        'longitude': 18.6466
    }
})
class PointField(serializers.Field):
    """
    Custom serializer field dla django.contrib.gis.db.models.fields.PointField.
    Konwertuje PostGIS Point na format {latitude, longitude} i odwrotnie.
    """
    def to_representation(self, value):
        """Konwertuje PostGIS Point na dict {latitude, longitude}."""
        if value is None:
            return None

        return {
            'latitude': value.y,
            'longitude': value.x,
        }

    def to_internal_value(self, data):
        """Konwertuje dict {latitude, longitude} na PostGIS Point."""
        if not isinstance(data, dict):
            raise serializers.ValidationError("Wspolrzedne musza byc w formacie obiektu.")

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Walidacja latitude
        if latitude is None:
            raise serializers.ValidationError({'latitude': 'Pole latitude jest wymagane.'})

        try:
            latitude = float(latitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'latitude': 'Nieprawidlowy format szerokosci geograficznej.'})

        if latitude < -90.0 or latitude > 90.0:
            raise serializers.ValidationError({'latitude': 'Szerokosc geograficzna musi byc w zakresie -90 do 90.'})

        # Walidacja longitude
        if longitude is None:
            raise serializers.ValidationError({'longitude': 'Pole longitude jest wymagane.'})

        try:
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'longitude': 'Nieprawidlowy format dlugosci geograficznej.'})

        if longitude < -180.0 or longitude > 180.0:
            raise serializers.ValidationError({'longitude': 'Dlugosc geograficzna musi byc w zakresie -180 do 180.'})

        # Utwórz PostGIS Point (longitude FIRST, latitude SECOND - standard WGS84)
        return Point(longitude, latitude, srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer dla modelu Location z obsluga PostGIS Point.
    Uzywa custom PointField do konwersji wspolrzednych.
    """
    coordinates = PointField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates']
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {
                'required': False,
                'allow_blank': False,
                'max_length': 200,
                'error_messages': {
                    'max_length': 'Nazwa lokalizacji nie moze byc dluzsza niz 200 znakow.',
                    'blank': 'Nazwa lokalizacji nie moze byc pusta.',
                }
            }
        }


class LocationListSerializer(serializers.ModelSerializer):
    """
    Serializer dla endpointu GET /api/locations/ z dodatkowym polem avg_emotional_value.
    Uzywany do wyswietlania listy lokalizacji z agregowanymi danymi emocji.
    """
    coordinates = PointField()
    avg_emotional_value = serializers.SerializerMethodField()
    emotion_points_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']
        read_only_fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']

    @extend_schema_field({
        'type': 'number',
        'format': 'float',
        'nullable': True,
        'description': 'Srednia wartosc emocjonalna (1-5) dla tej lokalizacji. '
                      'Liczy ze wszystkich publicznych emotion-points. '
                      'Null jesli lokalizacja nie ma zadnych emotion-points.',
        'example': 4.2
    })
    def get_avg_emotional_value(self, obj):
        """
        Zwraca srednia wartosc emocjonalna dla tej lokalizacji.
        Uzywa annotacji z queryset jesli dostepna, inaczej None.
        """
        return getattr(obj, 'avg_emotional_value', None)


class EmotionPointSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    location = LocationSerializer()

    class Meta:
        model = EmotionPoint
        fields = [
            'id',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'emotional_value': {
                'error_messages': {
                    'min_value': 'Wartosc emocjonalna musi byc w zakresie 1-5.',
                    'max_value': 'Wartosc emocjonalna musi byc w zakresie 1-5.',
                    'required': 'Pole emotional_value jest wymagane.',
                    'invalid': 'Nieprawidlowy format wartosci emocjonalnej.',
                }
            },
            'privacy_status': {
                'error_messages': {
                    'invalid_choice': 'Status prywatnosci musi byc "public" lub "private".',
                }
            }
        }

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        point = location_data['coordinates']
        custom_location_name = location_data.get('name', None)
        user = self.context['request'].user

        proximity_radius_meters = getattr(settings, 'CITYFEEL_LOCATION_PROXIMITY_RADIUS', 50)
        proximity_radius_degrees = proximity_radius_meters / 111320.0

        nearby_location = (
            Location.objects
            .filter(coordinates__dwithin=(point, proximity_radius_degrees))
            .annotate(distance=Distance('coordinates', point))
            .order_by('distance')
            .first()
        )

        if nearby_location:
            location = nearby_location
        else:
            if custom_location_name:
                location_name = custom_location_name
            else:
                location_name = f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"
            location = Location.objects.create(name=location_name, coordinates=point)

        try:
            emotion_point = EmotionPoint.objects.get(user=user, location=location)
            emotion_point.emotional_value = validated_data.get('emotional_value', emotion_point.emotional_value)
            emotion_point.privacy_status = validated_data.get('privacy_status', emotion_point.privacy_status)
            emotion_point.save()
        except EmotionPoint.DoesNotExist:
            emotion_point = EmotionPoint.objects.create(user=user, location=location, **validated_data)

        return emotion_point