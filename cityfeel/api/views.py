from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from emotions.models import EmotionPoint
from .serializers import EmotionPointSerializer


class EmotionPointViewSet(ModelViewSet):
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['emotional_value']
