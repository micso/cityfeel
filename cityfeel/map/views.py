from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.db.models import Avg, Count
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages

from emotions.models import EmotionPoint, Photo, Comment
from emotions.forms import PhotoForm
from emotions import sentiment as sentiment_service
from map.models import Location


class EmotionMapView(LoginRequiredMixin, TemplateView):
    template_name = 'map/emotion_map.html'
    login_url = reverse_lazy('cf_auth:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = {
            'CITYFEEL_LOCATION_PROXIMITY_RADIUS': settings.CITYFEEL_LOCATION_PROXIMITY_RADIUS
        }
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
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

        # 1. OPINIE (Oceny)
        # Po przejściu na model historyczny user może mieć wiele EmotionPoint per lokalizacja.
        # Lista pokazuje najnowszą ocenę każdego usera (DISTINCT ON (user_id)),
        # żeby UI nie duplikował tej samej osoby. Pełna historia jest widoczna na wykresie
        # w popupie / panelu lokalizacji.
        latest_per_user_ids = list(
            EmotionPoint.objects
            .filter(location=location)
            .order_by('user_id', '-created_at')
            .distinct('user_id')
            .values_list('id', flat=True)
        )
        ratings = (
            EmotionPoint.objects
            .filter(id__in=latest_per_user_ids)
            .select_related('user')
            .prefetch_related('related_comments')
            .order_by('-created_at')
        )

        # 2. KOMENTARZE (Samodzielne)
        # Filtrujemy tylko te, które NIE mają przypisanego emotion_point
        comments = (
            Comment.objects
            .filter(location=location, emotion_point__isnull=True)
            .select_related('user')
            .order_by('-created_at')
        )

        # 3. Dla "Samodzielnych Komentarzy":
        # Chcemy wiedzieć, czy ten user wystawił też ocenę (żeby pokazać badge z gwiazdką)
        ratings_by_user = {r.user_id: r for r in ratings}

        for c in comments:
            c.related_rating = ratings_by_user.get(c.user.id)

        # Zdjęcia i statystyki
        photos = location.photos.all().select_related('user').order_by('-created_at')

        emotion_distribution = (
            EmotionPoint.objects
            .filter(location=location)
            .values('emotional_value')
            .annotate(count=Count('id'))
            .order_by('emotional_value')
        )

        user_emotion_point = ratings_by_user.get(self.request.user.id)

        context.update({
            'ratings_list': ratings,
            'comments_list': comments,
            'photos': photos,
            'photo_form': PhotoForm(),
            'emotion_distribution': emotion_distribution,
            'user_emotion_point': user_emotion_point,
        })

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # 1. Dodawanie zdjęcia
        if 'image' in request.FILES:
            photo_form = PhotoForm(request.POST, request.FILES)
            if photo_form.is_valid():
                photo = photo_form.save(commit=False)
                photo.location = self.object
                photo.user = request.user
                photo.save()
                messages.success(request, 'Zdjęcie zostało dodane!')
            else:
                for error in photo_form.errors.values():
                    messages.error(request, error)
            return redirect('map:location_detail', pk=self.object.pk)

        # 2. Formularz Oceny i/lub Komentarza
        emotional_value = request.POST.get('emotional_value')
        privacy_status = request.POST.get('privacy_status', 'public')
        comment_content = request.POST.get('comment')
        comment_privacy = request.POST.get('comment_privacy_status', privacy_status)

        # Jeśli brak oceny, a jest komentarz — oblicz automatycznie z sentymentu
        if not emotional_value and comment_content and comment_content.strip():
            result = sentiment_service.analyze(comment_content.strip())
            if result['score'] is not None:
                emotional_value = str(round(result['score']))
                messages.info(request, f'Ocena obliczona automatycznie z treści komentarza: {emotional_value}/5')

        # A. SCENARIUSZ: Dodanie nowej Oceny (z opcjonalnym komentarzem).
        # Model jest historyczny: każdy klik = nowy EmotionPoint z własnym created_at.
        # Stare wpisy zostają — pozwalają na filtr czasowy mapy i wykres trendu lokalizacji.
        if emotional_value:
            emotion_point = EmotionPoint.objects.create(
                user=request.user,
                location=self.object,
                emotional_value=emotional_value,
                privacy_status=privacy_status,
            )
            messages.success(request, 'Twoja ocena została zapisana!')

            # Komentarz, jeśli podany, wiążemy z TĄ konkretną nową oceną.
            if comment_content and comment_content.strip():
                Comment.objects.create(
                    user=request.user,
                    location=self.object,
                    emotion_point=emotion_point,
                    content=comment_content.strip(),
                    privacy_status=privacy_status,
                )

        # B. SCENARIUSZ: Tylko Samodzielny Komentarz (bez wysyłania emotional_value)
        elif comment_content and comment_content.strip():
            Comment.objects.create(
                user=request.user,
                location=self.object,
                emotion_point=None,  # BRAK POWIĄZANIA
                content=comment_content.strip(),
                privacy_status=comment_privacy
            )
            messages.success(request, 'Twój komentarz został dodany!')

        return redirect('map:location_detail', pk=self.object.pk)