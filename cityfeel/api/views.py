from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Count, Q

from emotions.models import EmotionPoint, Comment
from map.models import Location
from auth.models import Friendship, CFUser
from .serializers import (
    EmotionPointSerializer, 
    LocationListSerializer, 
    FriendshipSerializer, 
    FriendUserSerializer,
    CommentSerializer
)
from .filters import LocationFilter, EmotionPointFilter


class EmotionPointViewSet(ModelViewSet):
    """
    ViewSet dla endpointu /api/emotion-points/.
    
    GET (lista): Zwraca tylko publiczne EmotionPoints (dla widoków profilowych itp.)
    POST/PUT/PATCH: Tworzy/aktualizuje EmotionPoints (publiczne i prywatne)
    
    Uwaga: Wszystkie EmotionPoints (publiczne i prywatne) są uwzględniane w statystykach
    lokalizacji w LocationViewSet. Różnica polega tylko na tym czy pokazujemy autora.
    
    Filtrowanie:
    - ?emotional_value=1,2,3 - filtrowanie po wielu wartościach emocjonalnych
    """
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmotionPointFilter


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
    pagination_class = None  # Wyłącz paginację - wszystkie lokalizacje w bounding box

    def get_queryset(self):
        return (
            Location.objects.all()
            .distinct()
            .annotate(
                avg_emotional_value=Avg('emotion_points__emotional_value'),
                emotion_points_count=Count('emotion_points')
            )
            .order_by('-avg_emotional_value', 'name')
        )


class FriendshipViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin,
                        GenericViewSet):
    """
    ViewSet dla systemu znajomych.
    
    POST /api/friendship/ - Wyślij zaproszenie (wymaga friend_id)
    PATCH /api/friendship/{id}/ - Akceptuj zaproszenie (body: {"status": "accepted"})
    DELETE /api/friendship/{id}/ - Odrzuć zaproszenie / Usuń znajomego
    GET /api/friends/ - (Action) Lista znajomych
    GET /api/friendship/requests/ - (Action) Lista oczekujących zaproszeń (otrzymanych)
    """
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Zwraca relacje, w których uczestniczy zalogowany użytkownik."""
        user = self.request.user
        return Friendship.objects.filter(Q(user=user) | Q(friend=user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='requests')
    def requests_list(self, request):
        """
        Zwraca listę otrzymanych, oczekujących zaproszeń.
        Endpoint: /api/friendship/requests/
        """
        incoming_requests = Friendship.objects.filter(
            friend=request.user,
            status=Friendship.PENDING
        ).order_by('-created_at')

        serializer = self.get_serializer(incoming_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='friends')
    def friends_list(self, request):
        """
        Zwraca listę znajomych (status ACCEPTED).
        Zwraca dane użytkowników, a nie obiekty Friendship.
        Endpoint: /api/friends/ (mapowane w urls.py)
        """
        user = request.user

        # Pobierz wszystkie zaakceptowane relacje
        friendships = Friendship.objects.filter(
            (Q(user=user) | Q(friend=user)) & Q(status=Friendship.ACCEPTED)
        ).select_related('user', 'friend')

        friends_data = []
        for f in friendships:
            # Wybierz "drugą stronę" relacji
            is_sender = f.user == user
            friend_user = f.friend if is_sender else f.user

            # Przygotuj dane do serializacji
            friend_user.friendship_id = f.id
            friend_user.friendship_since = f.created_at
            friends_data.append(friend_user)

        serializer = FriendUserSerializer(friends_data, many=True, context={'request': request})
        return Response(serializer.data)


class CommentViewSet(mixins.CreateModelMixin, GenericViewSet):
    """
    ViewSet dla komentarzy.
    Obsługuje tylko tworzenie (POST).
    Endpoint: /api/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Comment.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Dodaje nowy komentarz do punktu emocji.
        Wymaga: content, point_id.
        Automatycznie przypisuje zalogowanego użytkownika.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)