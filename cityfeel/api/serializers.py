from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from django.db.models import Q

from emotions.models import EmotionPoint, Comment
from map.models import Location
from auth.models import Friendship, CFUser


@extend_schema_field({
    'type': 'object',
    'properties': {
        'latitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -90.0,
            'maximum': 90.0,
            'description': 'Szerokość geograficzna'
        },
        'longitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -180.0,
            'maximum': 180.0,
            'description': 'Długość geograficzna'
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
            raise serializers.ValidationError("Współrzędne muszą być w formacie obiektu.")

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Walidacja latitude
        if latitude is None:
            raise serializers.ValidationError({'latitude': 'Pole latitude jest wymagane.'})
        try:
            latitude = float(latitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'latitude': 'Nieprawidłowy format szerokości geograficznej.'})

        if not -90 <= latitude <= 90:
            raise serializers.ValidationError({'latitude': 'Szerokość geograficzna musi być w zakresie -90 do 90.'})

        # Walidacja longitude
        if longitude is None:
            raise serializers.ValidationError({'longitude': 'Pole longitude jest wymagane.'})
        try:
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'longitude': 'Nieprawidłowy format długości geograficznej.'})

        if not -180 <= longitude <= 180:
            raise serializers.ValidationError({'longitude': 'Długość geograficzna musi być w zakresie -180 do 180.'})

        return Point(longitude, latitude, srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer dla modelu Location z obsługą PostGIS Point.
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
    """
    coordinates = PointField()
    avg_emotional_value = serializers.SerializerMethodField()
    emotion_points_count = serializers.IntegerField(read_only=True)
    latest_comment = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'coordinates',
            'avg_emotional_value', 'emotion_points_count',
            'latest_comment', 'comments_count'
        ]
        read_only_fields = fields

    def get_avg_emotional_value(self, obj):
        return getattr(obj, 'avg_emotional_value', None)

    @extend_schema_field({'type': 'integer'})
    def get_comments_count(self, obj):
        try:
            return obj.comments.count()
        except Exception:
            return 0

    @extend_schema_field({
        'type': 'object',
        'nullable': True,
        'description': 'Ostatni komentarz z uwzględnieniem prywatności.',
        'properties': {
            'username': {'type': 'string'},
            'content': {'type': 'string'},
            'emotional_value': {'type': 'integer', 'nullable': True}
        }
    })
    def get_latest_comment(self, obj):
        try:
            comment = obj.comments.select_related('user', 'emotion_point').order_by('-created_at').first()
            if comment:
                content = comment.content
                username = "Anonim" if comment.privacy_status == 'private' else comment.user.username

                data = {
                    'username': username,
                    'content': content[:100] + '...' if len(content) > 100 else content,
                }
                if comment.emotion_point:
                    data['emotional_value'] = comment.emotion_point.emotional_value
                return data
        except Exception:
            return None
        return None


class EmotionPointSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    location = LocationSerializer()
    comment = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = EmotionPoint
        fields = [
            'id',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
            'comment',
        ]
        read_only_fields = ['id']
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

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        comment_content = validated_data.pop('comment', None)
        point = location_data['coordinates']
        custom_location_name = location_data.get('name', None)
        user = self.context['request'].user

        proximity_meters = getattr(settings, 'CITYFEEL_LOCATION_PROXIMITY_RADIUS', 50)
        proximity_degrees = proximity_meters / 111320.0

        nearby_location = (
            Location.objects
            .filter(coordinates__dwithin=(point, proximity_degrees))
            .annotate(distance=Distance('coordinates', point))
            .order_by('distance')
            .first()
        )

        if nearby_location:
            location = nearby_location
        else:
            location_name = custom_location_name if custom_location_name else f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"
            location = Location.objects.create(name=location_name, coordinates=point)

        privacy_status = validated_data.get('privacy_status', 'public')

        emotion_point, _ = EmotionPoint.objects.update_or_create(
            user=user,
            location=location,
            defaults={
                'emotional_value': validated_data['emotional_value'],
                'privacy_status': privacy_status
            }
        )

        if comment_content and comment_content.strip():
            existing_comment = Comment.objects.filter(user=user, location=location, emotion_point=emotion_point).first()
            if existing_comment:
                existing_comment.content = comment_content.strip()
                existing_comment.privacy_status = privacy_status
                existing_comment.save()
            else:
                Comment.objects.create(
                    user=user,
                    location=location,
                    emotion_point=emotion_point,
                    content=comment_content.strip(),
                    privacy_status=privacy_status
                )

        return emotion_point


class FriendshipSerializer(serializers.ModelSerializer):
    friend_id = serializers.PrimaryKeyRelatedField(source='friend', queryset=CFUser.objects.all(), write_only=True)
    user = serializers.StringRelatedField(read_only=True)
    friend = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'user', 'friend', 'friend_id', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'friend', 'created_at']

    def validate(self, attrs):
        request = self.context['request']
        if self.instance is None:
            friend = attrs['friend']
            user = request.user
            if user == friend:
                raise serializers.ValidationError("Nie możesz wysłać zaproszenia do samego siebie.")
            if Friendship.objects.filter(
                    (Q(user=user) & Q(friend=friend)) | (Q(user=friend) & Q(friend=user))).exists():
                raise serializers.ValidationError(
                    "Relacja z tym użytkownikiem już istnieje (oczekująca lub zaakceptowana).")
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FriendUserSerializer(serializers.ModelSerializer):
    friendship_id = serializers.IntegerField(read_only=True)
    friendship_since = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CFUser
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'friendship_id', 'friendship_since']


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.all(),
        write_only=True,
        error_messages={'does_not_exist': 'Podana lokalizacja nie istnieje.'}
    )

    class Meta:
        model = Comment
        fields = ['id', 'username', 'content', 'created_at', 'location_id', 'privacy_status']
        read_only_fields = ['id', 'username', 'created_at']
        extra_kwargs = {
            'content': {'error_messages': {'blank': 'Treść nie może być pusta.'}}
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        if 'privacy_status' not in validated_data:
            validated_data['privacy_status'] = 'public'
        return super().create(validated_data)