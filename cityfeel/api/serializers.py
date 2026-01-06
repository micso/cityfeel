from rest_framework import serializers
from django.contrib.auth import get_user_model
from emotions.models import EmotionPoint
from map.models import Location
from social.models import Friendship

User = get_user_model()


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for locations."""

    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'average_rating', 'ratings_count']
        read_only_fields = ['average_rating', 'ratings_count']


class EmotionPointSerializer(serializers.ModelSerializer):
    """Serializer for emotion points."""
    user = serializers.StringRelatedField(read_only=True)
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source='location', write_only=True, required=False
    )

    # New fields for creating/updating location inline (optional)
    location_name = serializers.CharField(write_only=True, required=False)
    location_address = serializers.CharField(write_only=True, required=False)
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

    class Meta:
        model = EmotionPoint
        fields = [
            'id', 'user', 'location', 'location_id',
            'emotional_value', 'comment', 'privacy_status', 'created_at',
            'location_name', 'location_address', 'latitude', 'longitude'
        ]
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        # Extract location data fields
        lat = validated_data.pop('latitude', None)
        lng = validated_data.pop('longitude', None)
        loc_name = validated_data.pop('location_name', None)
        loc_addr = validated_data.pop('location_address', '')

        location = validated_data.get('location')

        # Logic: If no location ID provided, try to find or create by lat/lng
        if not location and lat is not None and lng is not None:
            # Simple proximity check or create logic could go here
            # For now, we create a new one if not provided
            location, created = Location.objects.get_or_create(
                latitude=lat,
                longitude=lng,
                defaults={'name': loc_name or 'Unknown', 'address': loc_addr}
            )
            validated_data['location'] = location

        return super().create(validated_data)


# --- SERIALIZERY SOCIAL (Przeniesione z social/serializers.py) ---

class UserSimpleSerializer(serializers.ModelSerializer):
    """Prosty serializer użytkownika do list znajomych."""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']
        read_only_fields = ['id', 'username', 'first_name', 'last_name', 'avatar']


class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer do wyświetlania relacji i zmiany statusu."""
    creator = UserSimpleSerializer(read_only=True)
    target = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'creator', 'target', 'status', 'created_at']
        read_only_fields = ['id', 'creator', 'target', 'created_at']

    def validate_status(self, value):
        """Pozwól tylko na akceptację lub odrzucenie."""
        if value not in ['accepted', 'rejected']:
            raise serializers.ValidationError("Status można zmienić tylko na 'accepted' lub 'rejected'.")
        return value


class FriendshipCreateSerializer(serializers.ModelSerializer):
    """Serializer do tworzenia (wysyłania) zaproszeń."""
    target_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'target_id', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate_target_id(self, value):
        user = self.context['request'].user

        # Walidacja: nie można zaprosić siebie
        if value == user.id:
            raise serializers.ValidationError("Nie możesz wysłać zaproszenia do samego siebie.")

        # Walidacja: użytkownik musi istnieć
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Użytkownik o podanym ID nie istnieje.")

        return value

    def validate(self, data):
        user = self.context['request'].user
        target_id = data['target_id']
        target = User.objects.get(id=target_id)

        # Walidacja: czy relacja już istnieje (tylko aktywne: pending/accepted)
        if Friendship.request_exists(user, target):
            raise serializers.ValidationError("Relacja z tym użytkownikiem już istnieje.")

        return data

    def create(self, validated_data):
        target = User.objects.get(id=validated_data['target_id'])
        creator = self.context['request'].user

        # Używamy update_or_create aby obsłużyć przypadek ponownego zaproszenia
        # po wcześniejszym odrzuceniu (status 'rejected').
        friendship, created = Friendship.objects.update_or_create(
            creator=creator,
            target=target,
            defaults={'status': 'pending'}
        )

        return friendship