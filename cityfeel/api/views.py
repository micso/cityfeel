from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from emotions.models import EmotionPoint
from .serializers import EmotionPointSerializer

class EmotionPointListAPIView(generics.ListAPIView):
    """
    GET /api/emotion-points/
    """
    # 1. QuerySet: Tylko publiczne punkty, sortowane od najnowszych
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')

    serializer_class = EmotionPointSerializer

    # 2. Permissions: Tylko dla zalogowanych
    permission_classes = [IsAuthenticated]

    # 3. Filtrowanie: Gotowy mechanizm Django Filter
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['emotional_value']