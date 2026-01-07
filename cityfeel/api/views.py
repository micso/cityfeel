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
    """
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmotionPointFilter


class LocationViewSet(ReadOnlyModelViewSet):
    """
    ViewSet dla endpointu /api/locations/ (READ-ONLY).
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter

    def get_queryset(self):
        return (
            Location.objects
            .annotate(
                avg_emotional_value=Avg('emotion_points__emotional_value'),
                emotion_points_count=Count('emotion_points')
            )
            .prefetch_related('emotion_points__user')
            .order_by('-avg_emotional_value', 'name')
        )


class FriendshipViewSet(mixins.CreateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin,
                        GenericViewSet):
    """
    ViewSet dla systemu znajomych.
    """
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(Q(user=user) | Q(friend=user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='requests')
    def requests_list(self, request):
        incoming_requests = Friendship.objects.filter(
            friend=request.user,
            status=Friendship.PENDING
        ).order_by('-created_at')

        serializer = self.get_serializer(incoming_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='friends')
    def friends_list(self, request):
        user = request.user
        friendships = Friendship.objects.filter(
            (Q(user=user) | Q(friend=user)) & Q(status=Friendship.ACCEPTED)
        ).select_related('user', 'friend')

        friends_data = []
        for f in friendships:
            is_sender = f.user == user
            friend_user = f.friend if is_sender else f.user
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
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)