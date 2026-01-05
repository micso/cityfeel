class LocationViewSet(ReadOnlyModelViewSet):
    """
    ViewSet dla endpointu /api/locations/ (READ-ONLY).
    Zwraca lokalizacje z agregowana srednia wartoscia emocjonalna punktow PUBLICZNYCH.
    """
    serializer_class = LocationListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LocationFilter

    def get_queryset(self):
        return (
            Location.objects
            .annotate(
                avg_emotional_value=Avg(
                    'emotion_points__emotional_value',
                    filter=Q(emotion_points__privacy_status='public')
                ),
                emotion_points_count=Count(
                    'emotion_points',
                    filter=Q(emotion_points__privacy_status='public')
                )
            )
            .order_by('-avg_emotional_value', 'name')
        )