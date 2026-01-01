from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.db.models import Q
from .models import EmotionPoint
from .serializers import EmotionPointSerializer

class EmotionPointListAPIView(generics.ListAPIView):
    """
    GET /api/emotion-points/
    """
    serializer_class = EmotionPointSerializer
    permission_classes = [AllowAny]  # Endpoint dostępny dla niezalogowanych

    def get_queryset(self):
        user = self.request.user
        # Sortowanie od najnowszych
        queryset = EmotionPoint.objects.select_related('user', 'location').order_by('-created_at')

        # 1. Logika Prywatności (zgodna z Twoim modelem)
        if user.is_authenticated:
            # Zalogowany widzi: status='public' LUB (status='private' I jest właścicielem)
            queryset = queryset.filter(
                Q(privacy_status='public') | Q(user=user)
            )
        else:
            # Niezalogowany widzi tylko status='public'
            queryset = queryset.filter(privacy_status='public')

        # 2. Filtrowanie po wartości emocji (?emotional_value=5)
        emotional_value = self.request.query_params.get('emotional_value')
        if emotional_value:
            queryset = queryset.filter(emotional_value=emotional_value)

        return queryset