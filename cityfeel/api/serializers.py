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
            'description': 'Latitude'
        },
        'longitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -180.0,
            'maximum': 180.0,
            'description': 'Longitude'
        }
    },
    'required': ['latitude', 'longitude']
})
class PointField(serializers.Field):
    """
    Custom serializer field for django.contrib.gis.db.models.fields.PointField.
    Converts between PostGIS Point and {latitude, longitude} dict.
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
            raise serializers.ValidationError("Coordinates must be an object.")
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is None or longitude is None:
            raise serializers.ValidationError("Both latitude and longitude are required.")
            
        try:
            return Point(float(longitude), float(latitude), srid=4326)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Invalid coordinates format.")


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for Location model.
    Task #35: Added average_rating and total_opinions.
    """
    coordinates = PointField()
    average_rating = serializers.FloatField(read_only=True)
    total_opinions = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates', 'average_rating', 'total_opinions']
        read_only_fields = ['id', 'average_rating', 'total_opinions']


class EmotionPointSerializer(serializers.ModelSerializer):
    """
    Serializer for EmotionPoint.
    Based on master with Task #35 requirements.
    """
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

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        point = location_data['coordinates']
        custom_name = location_data.get('name')
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
            name = custom_name if custom_name else f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"
            location = Location.objects.create(name=name, coordinates=point)

        emotion_point, _ = EmotionPoint.objects.update_or_create(
            user=user,
            location=location,
            defaults=validated_data
        )
        return emotion_point