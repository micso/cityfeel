from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.db.models import Avg, Count
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

from emotions.models import EmotionPoint, Photo
from map.models import Location
# Importujemy oba formularze
from emotions.forms import PhotoForm, CommentForm


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
    """Widok szczegółowy lokalizacji z publicznymi emotion points, zdjęciami i statystykami."""
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

        # Publiczne emotion points + komentarze (Twoja zmiana: prefetch comments)
        public_points = (
            EmotionPoint.objects
            .filter(location=location, privacy_status='public')
            .select_related('user')
            .prefetch_related('comments', 'comments__user')
            .order_by('-created_at')
        )

        # Zdjęcia lokalizacji (Zmiana z mastera)
        photos = location.photos.all().order_by('-created_at')

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
            'photos': photos,
            'photo_form': PhotoForm(),
            'emotion_distribution': emotion_distribution,
            'user_emotion_point': user_emotion_point,
            'comment_form': CommentForm(),  # Przekazanie formularza komentarza
        })

        return context

    def post(self, request, *args, **kwargs):
        """Obsługa formularzy POST (Zdjęcia i Oceny)."""
        self.object = self.get_object()
        
        # 1. Obsługa dodawania zdjęcia
        if 'image' in request.FILES:
            photo_form = PhotoForm(request.POST, request.FILES)
            if photo_form.is_valid():
                photo = photo_form.save(commit=False)
                photo.location = self.object
                photo.save()
                messages.success(request, 'Zdjęcie zostało dodane!')
            else:
                for error in photo_form.errors.values():
                    messages.error(request, error)
            return redirect('map:location_detail', pk=self.object.pk)

        # 2. Obsługa dodawania oceny (standardowy formularz fallback)
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