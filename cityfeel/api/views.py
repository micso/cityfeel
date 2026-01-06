from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from emotions.models import EmotionPoint
from .serializers import EmotionPointSerializer


class EmotionPointCreateView(CreateAPIView):
    """
    API endpoint dla tworzenia/aktualizacji EmotionPoint.

    POST /api/emotion-points/

    Request body:
    {
        "latitude": 52.2297,
        "longitude": 21.0122,
        "emotional_value": 4,
        "privacy_status": "public",  # opcjonalne, domyślnie "public"
        "location_name": "Plac Zamkowy"  # opcjonalne - auto-generowane jeśli nie podane
    }

    Response (201 Created - nowy punkt):
    {
        "id": 1,
        "latitude": 52.2297,
        "longitude": 21.0122,
        "emotional_value": 4,
        "privacy_status": "public",
        "location_id": 5,
        "location_name": "Lat: 52.2297, Lon: 21.0122",
        "created_at": "2025-01-03T10:30:00Z",
        "updated_at": "2025-01-03T10:30:00Z",
        "created": true,
        "updated": false
    }

    Response (200 OK - aktualizacja):
    {
        "id": 1,
        "latitude": 52.2297,
        "longitude": 21.0122,
        "emotional_value": 5,
        "privacy_status": "private",
        "location_id": 5,
        "location_name": "Lat: 52.2297, Lon: 21.0122",
        "created_at": "2025-01-03T10:30:00Z",
        "updated_at": "2025-01-03T11:45:00Z",
        "created": false,
        "updated": true
    }

    Wymaga autentykacji (IsAuthenticated).
    """

    queryset = EmotionPoint.objects.all()
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Nadpisana metoda create() aby zwrócić odpowiedni status code:
        - 201 Created dla nowego punktu
        - 200 OK dla aktualizacji istniejącego punktu
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Wykonaj create (który może być update)
        instance = serializer.save()

        # Sprawdź czy to była kreacja czy update
        was_created = getattr(instance, '_was_created', True)

        # Wybierz odpowiedni status code
        status_code = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK

        # Zwróć odpowiedź
        headers = self.get_success_headers(serializer.data) if was_created else {}
        return Response(
            serializer.data,
            status=status_code,
            headers=headers
        )
