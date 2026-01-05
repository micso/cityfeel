from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count

from emotions.models import EmotionPoint
from map.models import Location
from .serializers import EmotionPointSerializer, LocationListSerializer
from .filters import LocationFilter


class EmotionPointViewSet(ModelViewSet):
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['emotional_value']


class LocationViewSet(ReadOnlyModelViewSet):
    """
    ViewSet dla endpointu /api/locations/ (READ-ONLY).

    Zwraca lokalizacje z agregowana srednia wartoscia emocjonalna (avg_emotional_value).
    Srednia liczy ze WSZYSTKICH emotion_points (zarowno publicznych jak i prywatnych).
    Jest to zgodne z wymaganiami testow.
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter

    def get_queryset(self):
        """
        Zwraca queryset z annotacja avg_emotional_value i emotion_points_count.
        """
        return (
            Location.objects
            .annotate(
                avg_emotional_value=Avg('emotion_points__emotional_value'),
                emotion_points_count=Count('emotion_points')
            )
            .order_by('-avg_emotional_value', 'name')
        )