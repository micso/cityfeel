from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count

from emotions.models import EmotionPoint
from map.models import Location
from .serializers import EmotionPointSerializer, LocationListSerializer
from .filters import LocationFilter


class EmotionPointViewSet(ModelViewSet):
    """
    ViewSet dla endpointu /api/emotion-points/.

    GET (lista): Zwraca tylko publiczne EmotionPoints (dla widoków profilowych itp.)
    POST/PUT/PATCH: Tworzy/aktualizuje EmotionPoints (publiczne i prywatne)

    Uwaga: Wszystkie EmotionPoints (publiczne i prywatne) są uwzględniane w statystykach
    lokalizacji w LocationViewSet. Różnica polega tylko na tym czy pokazujemy autora.
    """
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['emotional_value']


class LocationViewSet(ReadOnlyModelViewSet):
    """
    ViewSet dla endpointu /api/locations/ (READ-ONLY).

    Zwraca lokalizacje z agregowaną średnią wartością emocjonalną (avg_emotional_value).
    Średnia liczy ze WSZYSTKICH emotion_points (zarówno publicznych jak i prywatnych).

    Filtrowanie:
    - ?name=Gdańsk - filtrowanie po nazwie (icontains)
    - ?lat=54.35&lon=18.64&radius=1000 - filtrowanie po promieniu (metry)
    - ?bbox=18.5,54.3,18.7,54.4 - filtrowanie po bounding box
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter

    def get_queryset(self):
        """
        Zwraca queryset z annotacją avg_emotional_value i emotion_points_count.
        Średnia liczy ze WSZYSTKICH emotion_points (publicznych i prywatnych).
        Lokalizacje bez emotion_points mają avg_emotional_value=null i count=0.
        """
        return (
            Location.objects
            .annotate(
                avg_emotional_value=Avg('emotion_points__emotional_value'),
                emotion_points_count=Count('emotion_points')
            )
            .prefetch_related('emotion_points__user')
            .order_by('-avg_emotional_value', 'name')
        )
