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
        'latitude': {'type': 'number'},
        'longitude': {'type': 'number'}
    },
    'required': ['latitude', 'longitude']
})
class PointField(serializers.Field):
    def to_representation(self, value):
        if value is None: return None
        return {'latitude': value.y, 'longitude': value.x}

    def to_internal_value(self, data):
        if not isinstance(data, dict): raise serializers.ValidationError("Współrzędne muszą być obiektem.")
        return Point(float(data.get('longitude')), float(data.get('latitude')), srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    coordinates = PointField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates']
        read_only_fields = ['id']


class LocationListSerializer(serializers.ModelSerializer):
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

    def get_avg_emotional_value(self, obj):
        return getattr(obj, 'avg_emotional_value', None)

    @extend_schema_field({'type': 'integer'})
    def get_comments_count(self, obj):
        return obj.comments.count()

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
            # Pobieramy najnowszy komentarz
            comment = obj.comments.select_related('user', 'emotion_point').order_by('-created_at').first()

            if comment:
                content = comment.content

                # [POPRAWKA 1] Obsługa anonimowości
                if comment.privacy_status == 'private':
                    username = "Anonim"
                else:
                    username = comment.user.username

                data = {
                    'username': username,
                    'content': content[:100] + '...' if len(content) > 100 else content,
                }

                # [POPRAWKA 2] Dodaj emotional_value TYLKO jeśli komentarz jest powiązany z oceną
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
            'id', 'location', 'emotional_value', 'privacy_status', 'username', 'comment'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        location_data = validated_data.pop('location')
        comment_content = validated_data.pop('comment', None)
        point = location_data['coordinates']
        custom_name = location_data.get('name')
        user = self.context['request'].user

        proximity_meters = getattr(settings, 'CITYFEEL_LOCATION_PROXIMITY_RADIUS', 50)
        proximity_degrees = proximity_meters / 111320.0

        nearby = Location.objects.filter(coordinates__dwithin=(point, proximity_degrees)) \
            .annotate(distance=Distance('coordinates', point)).order_by('distance').first()

        if nearby:
            location = nearby
        else:
            name = custom_name if custom_name else f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"
            location = Location.objects.create(name=name, coordinates=point)

        # 1. Zapisz EmotionPoint
        emotion_point, _ = EmotionPoint.objects.update_or_create(
            user=user,
            location=location,
            defaults={
                'emotional_value': validated_data['emotional_value'],
                'privacy_status': validated_data['privacy_status']
            }
        )

        # 2. Zapisz Komentarz (powiązany)
        if comment_content and comment_content.strip():
            existing_comment = Comment.objects.filter(user=user, location=location, emotion_point=emotion_point).first()
            if existing_comment:
                existing_comment.content = comment_content.strip()
                existing_comment.save()
            else:
                Comment.objects.create(
                    user=user,
                    location=location,
                    emotion_point=emotion_point,
                    content=comment_content.strip(),
                    privacy_status=validated_data['privacy_status']
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
        if self.instance is None:
            if self.context['request'].user == attrs['friend']: raise serializers.ValidationError("Błąd")
            if Friendship.objects.filter((Q(user=self.context['request'].user) & Q(friend=attrs['friend'])) | (
                    Q(user=attrs['friend']) & Q(
                friend=self.context['request'].user))).exists(): raise serializers.ValidationError("Już istnieje")
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
    location_id = serializers.PrimaryKeyRelatedField(source='location', queryset=Location.objects.all(),
                                                     write_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'username', 'content', 'created_at', 'location_id']
        read_only_fields = ['id', 'username', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)