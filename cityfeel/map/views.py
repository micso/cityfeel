from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.db.models import Avg, Count
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

from emotions.models import EmotionPoint
from map.models import Location


class EmotionMapView(LoginRequiredMixin, TemplateView):
    """Main emotion map view - requires authentication."""

    template_name = 'map/emotion_map.html'
    login_url = reverse_lazy('cf_auth:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = {
            'CITYFEEL_LOCATION_PROXIMITY_RADIUS': settings.CITYFEEL_LOCATION_PROXIMITY_RADIUS
        }
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
    """Widok szczegółowy lokalizacji z publicznymi emotion points i statystykami."""
    model = Location
    template_name = 'map/location_detail.html'
    context_object_name = 'location'
    login_url = reverse_lazy('cf_auth:login')

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
            .prefetch_related('comments')
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        emotional_value = request.POST.get('emotional_value')
        privacy_status = request.POST.get('privacy_status', 'public')

        if emotional_value:
            EmotionPoint.objects.update_or_create(
                user=request.user,
                location=self.object,
                defaults={
                    'emotional_value': emotional_value,
                    'privacy_status': privacy_status
                }
            )
            messages.success(request, 'Twoja ocena została zapisana!')
        
        return redirect('map:location_detail', pk=self.object.pk)