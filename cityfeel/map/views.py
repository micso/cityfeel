import os
import json
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView, ListView
from django.db.models import Avg, Count, Max, F, Q
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.contrib.gis.geos import GEOSGeometry

from emotions.models import EmotionPoint, Photo, Comment
from emotions.forms import PhotoForm
from map.models import Location


def get_raw_geojson_data():
    """Wyszukuje i ładuje surowy plik GeoJSON (do rysowania mapy i wyliczania granic)."""
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'export.geojson'),
        os.path.join(settings.BASE_DIR, '..', 'export.geojson'),
        '/app/export.geojson',
        '/app/cityfeel/export.geojson',
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'export.geojson')
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def get_all_districts():
    """Wczytuje dzielnice i zamienia je na matematyczne obrysy GEOSGeometry."""
    districts = cache.get('gdansk_districts_geometries')
    if districts:
        return districts

    data = get_raw_geojson_data()
    if not data:
        return {"❌ BŁĄD: Skopiuj plik export.geojson do folderu z manage.py!": None}

    districts = {}
    try:
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            name = props.get('name')
            geom = feature.get('geometry')

            # Bierzemy tylko poligony (twarde granice), ignorując punkty
            if name and geom and geom.get('type') in ['Polygon', 'MultiPolygon']:
                districts[name] = GEOSGeometry(json.dumps(geom))

        if not districts:
            return {"❌ BŁĄD: Plik znaleziony, ale brak poprawnych poligonów!": None}

        cache.set('gdansk_districts_geometries', districts, 60 * 60 * 24)
    except Exception as e:
        return {f"❌ BŁĄD PARSOWANIA: {str(e)[:30]}...": None}

    return districts


class EmotionMapView(LoginRequiredMixin, TemplateView):
    template_name = 'map/emotion_map.html'
    login_url = reverse_lazy('cf_auth:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = {
            'CITYFEEL_LOCATION_PROXIMITY_RADIUS': settings.CITYFEEL_LOCATION_PROXIMITY_RADIUS
        }
        return context


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'map/location_list.html'
    context_object_name = 'locations'
    paginate_by = 30
    login_url = reverse_lazy('cf_auth:login')

    def get_queryset(self):
        # Pobieramy LISTĘ dzielnic (Multi-Select)
        selected_districts = self.request.GET.getlist('district')
        min_rating = self.request.GET.get('min_rating')
        max_rating = self.request.GET.get('max_rating')
        has_photos = self.request.GET.get('has_photos')
        has_comments = self.request.GET.get('has_comments')
        sort_by = self.request.GET.get('sort_by', '-last_activity')

        qs = Location.objects.all()

        # 1. Geofencing dla WIELU dzielnic
        if selected_districts:
            districts_data = get_all_districts()
            district_query = Q()
            for d in selected_districts:
                if d in districts_data and districts_data[d]:
                    # Dodajemy warunek "LUB" dla każdej zaznaczonej dzielnicy
                    district_query |= Q(coordinates__intersects=districts_data[d])

            if district_query:
                qs = qs.filter(district_query)

        # 2. Szybka filtracja
        if has_photos == '1':
            qs = qs.filter(photos__isnull=False).distinct()
        if has_comments == '1':
            qs = qs.filter(comments__isnull=False).distinct()

        # 3. Adnotacje
        qs = qs.annotate(
            avg_emotional_value=Avg('emotion_points__emotional_value'),
            emotion_points_count=Count('emotion_points', distinct=True),
            comments_count=Count('comments', distinct=True),
            photos_count=Count('photos', distinct=True),
            last_activity=Max('emotion_points__created_at')
        )

        # 4. Filtracja Oceny Użytkownika
        if min_rating:
            try:
                qs = qs.filter(avg_emotional_value__gte=float(min_rating))
            except ValueError:
                pass

        if max_rating:
            try:
                qs = qs.filter(avg_emotional_value__lte=float(max_rating))
            except ValueError:
                pass

        # 5. Ostateczne sortowanie
        if sort_by == '-avg_emotional_value':
            qs = qs.order_by(F('avg_emotional_value').desc(nulls_last=True), '-emotion_points_count', 'name')
        elif sort_by == 'avg_emotional_value':
            qs = qs.order_by(F('avg_emotional_value').asc(nulls_last=True), '-emotion_points_count', 'name')
        elif sort_by == '-last_activity':
            qs = qs.order_by(F('last_activity').desc(nulls_last=True), 'name')
        elif sort_by == 'last_activity':
            qs = qs.order_by(F('last_activity').asc(nulls_last=True), 'name')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Przygotowanie danych mapy dla JS
        raw_geojson = get_raw_geojson_data()
        context['geojson_data'] = json.dumps(raw_geojson) if raw_geojson else "null"

        districts_data = get_all_districts()
        context['available_districts'] = sorted(districts_data.keys()) if districts_data else []

        # Bezpieczne przekazanie zaznaczonych dzielnic do JS
        context['current_districts_json'] = json.dumps(self.request.GET.getlist('district'))

        # Zapisujemy parametry URL (by paginacja pamiętała wszystkie dzielnice!)
        q = self.request.GET.copy()
        if 'page' in q:
            q.pop('page')
        context['query_string'] = q.urlencode()

        context['current_sort'] = self.request.GET.get('sort_by', '-last_activity')
        context['min_rating'] = self.request.GET.get('min_rating', '')
        context['max_rating'] = self.request.GET.get('max_rating', '')
        context['has_photos'] = self.request.GET.get('has_photos', '')
        context['has_comments'] = self.request.GET.get('has_comments', '')
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

        latest_per_user_ids = list(
            EmotionPoint.objects
            .filter(location=location)
            .order_by('user_id', '-created_at')
            .distinct('user_id')
            .values_list('id', flat=True)[:50]
        )
        ratings = (
            EmotionPoint.objects
            .filter(id__in=latest_per_user_ids)
            .select_related('user')
            .prefetch_related('related_comments')
            .order_by('-created_at')
        )

        comments = (
            Comment.objects
            .filter(location=location, emotion_point__isnull=True)
            .select_related('user')
            .order_by('-created_at')
        )

        ratings_by_user = {r.user_id: r for r in ratings}
        for c in comments:
            c.related_rating = ratings_by_user.get(c.user.id)

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

        emotional_value = request.POST.get('emotional_value')
        privacy_status = request.POST.get('privacy_status', 'public')
        comment_content = request.POST.get('comment')
        comment_privacy = request.POST.get('comment_privacy_status', privacy_status)

        if emotional_value:
            emotion_point = EmotionPoint.objects.create(
                user=request.user,
                location=self.object,
                emotional_value=emotional_value,
                privacy_status=privacy_status,
            )
            messages.success(request, 'Twoja ocena została zapisana!')

            if comment_content and comment_content.strip():
                Comment.objects.create(
                    user=request.user,
                    location=self.object,
                    emotion_point=emotion_point,
                    content=comment_content.strip(),
                    privacy_status=privacy_status,
                )
        elif comment_content and comment_content.strip():
            Comment.objects.create(
                user=request.user,
                location=self.object,
                emotion_point=None,
                content=comment_content.strip(),
                privacy_status=comment_privacy
            )
            messages.success(request, 'Twój komentarz został dodany!')

        return redirect('map:location_detail', pk=self.object.pk)