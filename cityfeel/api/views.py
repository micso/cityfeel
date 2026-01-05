from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q

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
    Srednia liczy sie tylko z PUBLICZNYCH emotion_points.

    Filtrowanie:
    - ?name=Gdansk - filtrowanie po nazwie (icontains)
    - ?lat=54.35&lon=18.64&radius=1000 - filtrowanie po promieniu (metry)
    - ?bbox=18.5,54.3,18.7,54.4 - filtrowanie po bounding box
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter

    def get_queryset(self):
        """
        Zwraca queryset z annotacja avg_emotional_value i emotion_points_count.
        Srednia liczy sie tylko z PUBLICZNYCH emotion_points.
        Lokalizacje bez publicznych emotion_points maja avg_emotional_value=null i count=0.
        """
        return (
            Location.objects
            .annotate(
                avg_emotional_value=Avg(
                    'emotion_points__emotional_value',
                    filter=Q(emotion_points__privacy_status='public')
                ),
                emotion_points_count=Count(
                    'emotion_points',
                    filter=Q(emotion_points__privacy_status='public')
                )
            )
            .order_by('-avg_emotional_value', 'name')
        )