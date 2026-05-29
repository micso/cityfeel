from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Max, F
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, TruncMonth
from django.utils.dateparse import parse_datetime
from django.core.cache import cache
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance

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
    queryset = EmotionPoint.objects.filter(privacy_status='public').order_by('-created_at')
    serializer_class = EmotionPointSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmotionPointFilter

    @action(detail=False, methods=['get'], url_path='histogram')
    def histogram(self, request):
        query_string = request.META.get('QUERY_STRING', '')
        cache_key = f"hist_data_{hash(query_string)}"

        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        bucket_name = request.query_params.get('bucket', DEFAULT_BUCKET)
        trunc = BUCKET_TRUNC.get(bucket_name)
        if trunc is None:
            return Response({'detail': f"Niepoprawny bucket."}, status=status.HTTP_400_BAD_REQUEST)

        base_qs = EmotionPoint.objects.all()
        filtered = self.filterset_class(request.query_params, queryset=base_qs).qs

        buckets = (
            filtered
            .annotate(bucket=trunc('created_at'))
            .values('bucket')
            .annotate(count=Count('id'), avg_value=Avg('emotional_value'))
            .order_by('bucket')
        )

        response_data = [
            {
                'bucket': b['bucket'].isoformat() if b['bucket'] else None,
                'count': b['count'],
                'avg_value': float(b['avg_value']) if b['avg_value'] is not None else None,
            }
            for b in buckets
        ]

        cache.set(cache_key, response_data, 300)
        return Response(response_data)


class LocationViewSet(ReadOnlyModelViewSet):
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter
    pagination_class = None

    def get_queryset(self):
        request = self.request
        base = Location.objects.all()

        # 1. Bounding Box (Cięcie ekranu)
        bbox_param = request.query_params.get('bbox')
        if bbox_param:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox_param.split(','))
                from django.contrib.gis.geos import Polygon
                bbox_polygon = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
                base = base.filter(coordinates__contained=bbox_polygon)
            except (ValueError, TypeError):
                pass

        # 2. Sprawdzamy czas ZANIM wyciągniemy TOP 100
        ca = parse_datetime(request.query_params.get('created_after', '') or '') if request else None
        cb = parse_datetime(request.query_params.get('created_before', '') or '') if request else None

        if ca and cb:
            # Włączony filtr czasu:
            # Wyszukujemy miejsca aktywne TYLKO w tym oknie czasowym
            time_filter = Q(emotion_points__created_at__gte=ca) & Q(emotion_points__created_at__lte=cb)

            fast_ids = list(
                base.filter(time_filter)  # Odrzucamy miejsca "z przyszłości" i martwe w tym czasie
                .annotate(last_activity=Max('emotion_points__created_at', filter=time_filter))
                .order_by(F('last_activity').desc(nulls_last=True))
                .values_list('id', flat=True)[:100]
            )
        else:
            # Domyślnie (Brak filtra): 100 najświeższych punktów z całego życia aplikacji
            fast_ids = list(
                base.annotate(last_activity=Max('emotion_points__created_at'))
                .order_by(F('last_activity').desc(nulls_last=True))
                .values_list('id', flat=True)[:100]
            )

        # 3. Zasilamy znalezioną historyczną setkę dokładnymi statystykami
        qs = Location.objects.filter(id__in=fast_ids)

        if ca and cb:
            qs = annotate_windowed_mean_of_means_avg(qs, ca, cb)
        else:
            qs = annotate_latest_per_user_avg(qs)

        return qs

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        """
        Zwraca WSZYSTKIE punkty w małym Bounding Boxie jako listę.
        Obliczanie dokładnej odległości i wybór najbliższego
        przenosimy do JavaScriptu, co gwarantuje 100% dokładności.
        """
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = request.query_params.get('radius', 50)

        if not lat or not lon:
            return Response({'detail': 'Brak współrzędnych.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deg = float(radius) / 111320.0
            min_lon, max_lon = float(lon) - deg, float(lon) + deg
            min_lat, max_lat = float(lat) - deg, float(lat) + deg

            from django.contrib.gis.geos import Polygon
            bbox_polygon = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))

            locations = Location.objects.filter(coordinates__contained=bbox_polygon)

            data = []
            for loc in locations:
                data.append({
                    'id': loc.id,
                    'name': loc.name,
                    'lat': loc.coordinates.y,
                    'lon': loc.coordinates.x
                })

            return Response(data)

        except Exception as e:
            print(f"Błąd wyszukiwania pobliskich punktów: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='emotion-timeline')
    def emotion_timeline(self, request, pk=None):
        bucket_name = request.query_params.get('bucket', DEFAULT_BUCKET)
        trunc = BUCKET_TRUNC.get(bucket_name)
        if trunc is None:
            return Response({'detail': f"Niepoprawny bucket."}, status=status.HTTP_400_BAD_REQUEST)

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


class FriendshipViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin, GenericViewSet):
    serializer_class = FriendshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friendship.objects.filter(Q(user=user) | Q(friend=user))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='requests')
    def requests_list(self, request):
        incoming_requests = Friendship.objects.filter(friend=request.user, status=Friendship.PENDING).order_by(
            '-created_at')
        serializer = self.get_serializer(incoming_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='friends')
    def friends_list(self, request):
        user = request.user
        friendships = Friendship.objects.filter(
            (Q(user=user) | Q(friend=user)) & Q(status=Friendship.ACCEPTED)).select_related('user', 'friend')
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
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Comment.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ReportViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    queryset = Report.objects.all()