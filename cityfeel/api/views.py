from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.contrib.auth import get_user_model

from emotions.models import EmotionPoint
from map.models import Location
from social.models import Friendship

from .serializers import (
    EmotionPointSerializer,
    LocationSerializer,
    FriendshipSerializer,
    FriendshipCreateSerializer,
    UserSimpleSerializer
)

User = get_user_model()


class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing locations.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class EmotionPointViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing emotion points.
    """
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Filter logic can be added here (e.g., by viewport bounds)
        return EmotionPoint.objects.all().select_related('location', 'user')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# --- WIDOKI SOCIAL (Przeniesione z social/views.py) ---

class FriendshipViewSet(viewsets.ModelViewSet):
    """
    API do zarządzania znajomościami.
    """
    permission_classes = [IsAuthenticated]
    # Dodano 'delete' do dozwolonych metod
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        """Zwraca wszystkie relacje użytkownika (wysłane i odebrane)."""
        user = self.request.user
        return Friendship.objects.filter(
            Q(creator=user) | Q(target=user)
        ).select_related('creator', 'target')

    def get_serializer_class(self):
        if self.action == 'create':
            return FriendshipCreateSerializer
        return FriendshipSerializer

    def perform_update(self, serializer):
        """Tylko odbiorca zaproszenia może zmienić status (akceptować/odrzucać)."""
        instance = self.get_object()
        # Jeśli zmieniamy status, sprawdzamy czy user jest targetem
        if 'status' in serializer.validated_data and instance.target != self.request.user:
            raise PermissionDenied("Tylko odbiorca zaproszenia może zmienić jego status.")
        serializer.save()

    def perform_destroy(self, instance):
        """Usuwanie znajomego lub wycofanie zaproszenia."""
        user = self.request.user
        # Tylko uczestnicy relacji mogą ją usunąć
        if instance.creator != user and instance.target != user:
            raise PermissionDenied("Nie możesz usunąć relacji, która nie należy do Ciebie.")
        instance.delete()

    @action(detail=False, methods=['get'])
    def requests(self, request):
        """
        GET /api/friendship/requests/
        Zwraca oczekujące zaproszenia skierowane DO użytkownika.
        """
        pending_requests = Friendship.objects.filter(
            target=request.user,
            status='pending'
        ).select_related('creator')

        serializer = FriendshipSerializer(pending_requests, many=True)
        return Response(serializer.data)


class FriendListView(generics.ListAPIView):
    """
    GET /api/friends/
    Zwraca listę znajomych (User objects).
    """
    serializer_class = UserSimpleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Pobierz ID znajomych z zaproszeń wysłanych przez użytkownika
        created_friends = Friendship.objects.filter(
            creator=user, status='accepted'
        ).values_list('target_id', flat=True)

        # Pobierz ID znajomych z zaproszeń otrzymanych przez użytkownika
        received_friends = Friendship.objects.filter(
            target=user, status='accepted'
        ).values_list('creator_id', flat=True)

        # Połącz listy ID
        all_friend_ids = list(created_friends) + list(received_friends)

        return User.objects.filter(id__in=all_friend_ids)