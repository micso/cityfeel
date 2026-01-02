from rest_framework import serializers
from .models import EmotionPoint, Comment, Photo

class EmotionPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmotionPoint
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ('user', 'created_at')

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = '__all__'
        read_only_fields = ('uploaded_at',)