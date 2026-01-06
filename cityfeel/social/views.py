from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Friendship
from .serializers import (
    FriendshipSerializer,
    FriendshipCreateSerializer,
    UserSimpleSerializer
)

User = get_user_model()


class FriendshipViewSet(viewsets.ModelViewSet):
    """
    API do zarządzania znajomościami.
    """
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

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
        """Tylko odbiorca zaproszenia może zmienić status."""
        instance = self.get_object()
        if instance.target != self.request.user:
            raise PermissionDenied("Tylko odbiorca zaproszenia może zmienić jego status.")
        serializer.save()

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


class FriendsPageView(LoginRequiredMixin, TemplateView):
    """
    Widok renderujący stronę HTML z listą znajomych i zaproszeniami.
    """
    template_name = 'social/friends.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Pobierz oczekujące zaproszenia (gdzie user jest celem)
        context['pending_requests'] = Friendship.objects.filter(
            target=user,
            status='pending'
        ).select_related('creator')

        # 2. Pobierz znajomych (logika identyczna jak w FriendListView)
        created_friends = Friendship.objects.filter(
            creator=user, status='accepted'
        ).values_list('target_id', flat=True)

        received_friends = Friendship.objects.filter(
            target=user, status='accepted'
        ).values_list('creator_id', flat=True)

        all_friend_ids = list(created_friends) + list(received_friends)
        context['friends'] = User.objects.filter(id__in=all_friend_ids)

        return context