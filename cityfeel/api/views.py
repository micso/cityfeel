# cityfeel/api/views.py

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, TruncMonth
from django.utils.dateparse import parse_datetime


# Mapowanie parametru ?bucket=... na funkcję truncującą (PostgreSQL date_trunc).
# Używane przez endpointy histogram i timeline.
BUCKET_TRUNC = {
    'hour': TruncHour,
    'day': TruncDay,
    'week': TruncWeek,
    'month': TruncMonth,
}
DEFAULT_BUCKET = 'day'

from emotions.models import EmotionPoint, Comment, Report
from map.models import Location
from auth.models import Friendship, CFUser
from .serializers import (
    EmotionPointSerializer,
    LocationListSerializer,
    FriendshipSerializer,
    FriendUserSerializer,
    CommentSerializer,
    ReportSerializer
)
from .filters import LocationFilter, EmotionPointFilter
from .aggregation import (
    annotate_latest_per_user_avg,
    annotate_windowed_mean_of_means_avg,
)


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

    @action(detail=False, methods=['get'], url_path='histogram')
    def histogram(self, request):
        """
        Zwraca histogram aktywności emocji w czasie — dane do paska histogramu
        pod mapą oraz do animacji "play".

        Endpoint: ``GET /api/emotion-points/histogram/``

        Query params (kompozycja AND z filtrami EmotionPointFilter):
            ``bucket``: ``hour`` | ``day`` (default) | ``week`` | ``month``
            ``bbox``, ``emotional_value``, ``created_after``, ``created_before``

        Zwraca listę kubełków posortowaną chronologicznie:
            ``[{"bucket": "2025-12-31T00:00:00Z", "count": 42, "avg_value": 3.7}, ...]``
        """
        bucket_name = request.query_params.get('bucket', DEFAULT_BUCKET)
        trunc = BUCKET_TRUNC.get(bucket_name)
        if trunc is None:
            return Response(
                {'detail': f"Niepoprawny bucket. Dozwolone: {sorted(BUCKET_TRUNC)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Histogram budujemy ze WSZYSTKICH wpisów (public+private) — public/private
        # wpływa tylko na widoczność autora, nie na statystyki.
        base_qs = EmotionPoint.objects.all()
        filtered = self.filterset_class(request.query_params, queryset=base_qs).qs

        buckets = (
            filtered
            .annotate(bucket=trunc('created_at'))
            .values('bucket')
            .annotate(count=Count('id'), avg_value=Avg('emotional_value'))
            .order_by('bucket')
        )

        return Response([
            {
                'bucket': b['bucket'].isoformat() if b['bucket'] else None,
                'count': b['count'],
                'avg_value': float(b['avg_value']) if b['avg_value'] is not None else None,
            }
            for b in buckets
        ])


class LocationViewSet(ReadOnlyModelViewSet):
    """
    ViewSet dla endpointu /api/locations/ (READ-ONLY).

    Zwraca lokalizacje z agregowaną średnią wartością emocjonalną (``avg_emotional_value``).
    Model EmotionPoint jest historyczny — średnia liczona w jednym z dwóch trybów:

    - **Tryb A (stan bieżący)** — używany domyślnie. Średnia z najnowszych głosów każdego usera
      (DISTINCT ON (user_id) ORDER BY created_at DESC).
    - **Tryb B (w oknie czasu)** — gdy podano ``?created_after`` i/lub ``?created_before``.
      Mean-of-means: każdy user ma jedną wagę w oknie niezależnie od liczby wpisów.

    Filtrowanie (kompozycja AND):
    - ``?name=Gdańsk`` — filtrowanie po nazwie (icontains)
    - ``?lat=54.35&lon=18.64&radius=1000`` — filtrowanie po promieniu (metry)
    - ``?bbox=18.5,54.3,18.7,54.4`` — filtrowanie po bounding box
    - ``?emotional_value=1,2,3`` — filtrowanie po średniej (po agregacji)
    - ``?created_after=2025-12-31T00:00:00Z&created_before=2026-01-01T00:00:00Z`` — okno czasu
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter
    pagination_class = None  # Wyłącz paginację - wszystkie lokalizacje w bounding box

    def get_queryset(self):
        # Tryb agregacji wybierany na podstawie obecności filtra czasu w query params.
        # Walidację formatu zostawiamy IsoDateTimeFilter w EmotionPointFilter (gdy będzie
        # propagowany), tu tylko parsujemy do datetime; niepoprawne wartości → tryb A.
        request = self.request
        ca = parse_datetime(request.query_params.get('created_after', '') or '') if request else None
        cb = parse_datetime(request.query_params.get('created_before', '') or '') if request else None

        base = Location.objects.all().distinct()
        if ca and cb:
            qs = annotate_windowed_mean_of_means_avg(base, ca, cb)
        else:
            qs = annotate_latest_per_user_avg(base)

        return qs.order_by('-avg_emotional_value', 'name')

    @action(detail=True, methods=['get'], url_path='emotion-timeline')
    def emotion_timeline(self, request, pk=None):
        """
        Zwraca timeline emocji dla konkretnej lokalizacji — dane do mini-wykresu
        w popupie markera.

        Endpoint: ``GET /api/locations/{id}/emotion-timeline/``

        Query params:
            ``bucket``: ``hour`` | ``day`` (default) | ``week`` | ``month``
            ``created_after``, ``created_before``: opcjonalne ograniczenie zakresu

        Zwraca listę chronologiczną:
            ``[{"bucket": "2025-12-31T00:00:00Z", "avg_value": 3.7, "count": 12}, ...]``

        Uwaga: tu używamy prostej średniej (mean of all entries in bucket), nie
        mean-of-means — bucket jest na tyle wąski, że pojedynczy user rzadko ma
        w nim wiele wpisów. Dla wykresu trendu prostota czytelności wygrywa.
        """
        bucket_name = request.query_params.get('bucket', DEFAULT_BUCKET)
        trunc = BUCKET_TRUNC.get(bucket_name)
        if trunc is None:
            return Response(
                {'detail': f"Niepoprawny bucket. Dozwolone: {sorted(BUCKET_TRUNC)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = EmotionPoint.objects.filter(location_id=pk)

        ca = parse_datetime(request.query_params.get('created_after', '') or '')
        cb = parse_datetime(request.query_params.get('created_before', '') or '')
        if ca:
            qs = qs.filter(created_at__gte=ca)
        if cb:
            qs = qs.filter(created_at__lte=cb)

        buckets = (
            qs
            .annotate(bucket=trunc('created_at'))
            .values('bucket')
            .annotate(avg_value=Avg('emotional_value'), count=Count('id'))
            .order_by('bucket')
        )

        return Response([
            {
                'bucket': b['bucket'].isoformat() if b['bucket'] else None,
                'avg_value': float(b['avg_value']) if b['avg_value'] is not None else None,
                'count': b['count'],
            }
            for b in buckets
        ])


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


class ReportViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.all()