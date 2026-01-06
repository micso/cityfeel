from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Friendship

User = get_user_model()


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