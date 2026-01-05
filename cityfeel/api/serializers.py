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
        if value is None:
            return None
        return {
            'latitude': value.y,
            'longitude': value.x,
        }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Wspolrzedne musza byc w formacie obiektu.")

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is None:
            raise serializers.ValidationError({'latitude': 'Pole latitude jest wymagane.'})
        try:
            latitude = float(latitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'latitude': 'Nieprawidlowy format szerokosci geograficznej.'})
        if latitude < -90.0 or latitude > 90.0:
            raise serializers.ValidationError({'latitude': 'Szerokosc geograficzna musi byc w zakresie -90 do 90.'})

        if longitude is None:
            raise serializers.ValidationError({'longitude': 'Pole longitude jest wymagane.'})
        try:
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'longitude': 'Nieprawidlowy format dlugosci geograficznej.'})
        if longitude < -180.0 or longitude > 180.0:
            raise serializers.ValidationError({'longitude': 'Dlugosc geograficzna musi byc w zakresie -180 do 180.'})

        return Point(longitude, latitude, srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    """
    Podstawowy serializer dla modelu Location.
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
            }
        }


class LocationListSerializer(serializers.ModelSerializer):
    """
    Serializer dla endpointu GET /api/locations/.
    Zwraca avg_emotional_value i emotion_points_count.
    """
    coordinates = PointField()
    avg_emotional_value = serializers.FloatField(read_only=True)
    emotion_points_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']
        read_only_fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']


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
            location_name = custom_location_name if custom_location_name else f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"
            location = Location.objects.create(name=location_name, coordinates=point)

        try:
            emotion_point = EmotionPoint.objects.get(user=user, location=location)
            emotion_point.emotional_value = validated_data.get('emotional_value', emotion_point.emotional_value)
            emotion_point.privacy_status = validated_data.get('privacy_status', emotion_point.privacy_status)
            emotion_point.save()
        except EmotionPoint.DoesNotExist:
            emotion_point = EmotionPoint.objects.create(user=user, location=location, **validated_data)

        return emotion_point