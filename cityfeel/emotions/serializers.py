from rest_framework import serializers
from .models import EmotionPoint

class EmotionPointSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)  # Dodajemy czytelną nazwę usera

    class Meta:
        model = EmotionPoint
        fields = ['id', 'user', 'username', 'location', 'emotional_value', 'privacy_status', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']