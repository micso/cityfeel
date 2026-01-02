from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class EmotionMapView(LoginRequiredMixin, TemplateView):
    """Main emotion map view - requires authentication."""

    template_name = 'map/emotion_map.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: Add emotion points data when API is ready
        # context['emotion_points'] = EmotionPoint.objects.filter(privacy_status='public')
        return context
