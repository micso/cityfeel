from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.db.models import Avg, Count

from emotions.models import EmotionPoint
from map.models import Location


class EmotionMapView(LoginRequiredMixin, TemplateView):
    """Main emotion map view - requires authentication."""

    template_name = 'map/emotion_map.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Add emotion points data when API is ready
        # context['emotion_points'] = EmotionPoint.objects.filter(privacy_status='public')
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
    """Widok szczegółowy lokalizacji z publicznymi emotion points i statystykami."""
    model = Location
    template_name = 'map/location_detail.html'
    context_object_name = 'location'
    login_url = '/auth/login/'

    def get_queryset(self):
        return Location.objects.annotate(
            avg_emotional_value=Avg('emotion_points__emotional_value'),
            emotion_points_count=Count('emotion_points')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location = self.object

        # Publiczne emotion points
        public_points = (
            EmotionPoint.objects
            .filter(location=location, privacy_status='public')
            .select_related('user')
            .prefetch_related('comment_set')
            .order_by('-created_at')
        )

        # Statystyki rozkładu ocen (1-5)
        emotion_distribution = (
            EmotionPoint.objects
            .filter(location=location)
            .values('emotional_value')
            .annotate(count=Count('id'))
            .order_by('emotional_value')
        )

        # Czy user już ocenił?
        user_emotion_point = EmotionPoint.objects.filter(
            location=location,
            user=self.request.user
        ).first()

        context.update({
            'public_points': public_points,
            'emotion_distribution': emotion_distribution,
            'user_emotion_point': user_emotion_point,
        })

        return context
