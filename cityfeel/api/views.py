from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q

from emotions.models import EmotionPoint
from map.models import Location
from .serializers import EmotionPointSerializer, LocationSerializer


class EmotionPointViewSet(ModelViewSet):
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['emotional_value']


class LocationViewSet(ModelViewSet):
    """
    Endpoint GET /api/locations/
    Zadanie #35: Zwraca srednia ocene i liczbe opinii.
    """
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return Location.objects.annotate(
            average_rating=Avg(
                'emotion_points__emotional_value',
                filter=Q(emotion_points__privacy_status='public')
            ),
            total_opinions=Count(
                'emotion_points',
                filter=Q(emotion_points__privacy_status='public')
            )
        ).order_by('-total_opinions')