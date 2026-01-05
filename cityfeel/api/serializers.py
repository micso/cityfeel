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
        if not (-90.0 <= latitude <= 90.0):
            raise serializers.ValidationError({'latitude': 'Szerokosc geograficzna musi byc w zakresie -90 do 90.'})

        if longitude is None:
            raise serializers.ValidationError({'longitude': 'Pole longitude jest wymagane.'})
        try:
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'longitude': 'Nieprawidlowy format dlugosci geograficznej.'})
        if not (-180.0 <= longitude <= 180.0):
            raise serializers.ValidationError({'longitude': 'Dlugosc geograficzna musi byc w zakresie -180 do 180.'})

        return Point(longitude, latitude, srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer dla modelu Location.
    Zadanie #35: Dodano average_rating i total_opinions.
    """
    coordinates = PointField()
    average_rating = serializers.FloatField(read_only=True)
    total_opinions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates', 'average_rating', 'total_opinions']
        read_only_fields = ['id', 'average_rating', 'total_opinions']
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


class EmotionPointSerializer(serializers.ModelSerializer):
    """
    Serializer dla EmotionPoint.
    Obsluguje tworzenie punktu na podstawie wspolrzednych.
    """
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)
    location_name = serializers.CharField(required=False, write_only=True)
    
    username = serializers.CharField(source='user.username', read_only=True)
    location = LocationSerializer(read_only=True)

    class Meta:
        model = EmotionPoint
        fields = [
            'id',
            'latitude', 'longitude', 'location_name',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
        ]
        read_only_fields = ['id', 'location']

    def create(self, validated_data):
        lat = validated_data.pop('latitude')
        lon = validated_data.pop('longitude')
        custom_name = validated_data.pop('location_name', None)
        user = self.context['request'].user
        point = Point(lon, lat, srid=4326)

        radius = getattr(settings, 'CITYFEEL_LOCATION_PROXIMITY_RADIUS', 50) / 111320.0
        location = Location.objects.filter(
            coordinates__dwithin=(point, radius)
        ).annotate(distance=Distance('coordinates', point)).order_by('distance').first()

        if not location:
            name = custom_name if custom_name else f"Lat: {lat:.4f}, Lon: {lon:.4f}"
            location = Location.objects.create(name=name, coordinates=point)

        emotion_point, _ = EmotionPoint.objects.update_or_create(
            user=user,
            location=location,
            defaults=validated_data
        )
        return emotion_point

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.location and instance.location.coordinates:
            ret['latitude'] = instance.location.coordinates.y
            ret['longitude'] = instance.location.coordinates.x
        return ret