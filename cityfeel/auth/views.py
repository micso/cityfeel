from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, UpdateView, ListView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Q, Prefetch

from .forms import UserRegistrationForm, UserProfileEditForm
from .models import CFUser
from emotions.models import EmotionPoint


class RegisterView(CreateView):
    """User registration view."""

    form_class = UserRegistrationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('map:emotion_map')

    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)

        # Log the user in automatically after registration
        login(self.request, self.object)

        messages.success(
            self.request,
            f'Witaj, {self.object.username}! Twoje konto zostało utworzone.'
        )
        return response

    def get(self, request, *args, **kwargs):
        # Redirect if user is already logged in
        if request.user.is_authenticated:
            return redirect('map:emotion_map')
        return super().get(request, *args, **kwargs)


class UserProfileView(LoginRequiredMixin, DetailView):
    """Display user profile with emotion points statistics."""

    model = CFUser
    template_name = 'auth/profile.html'
    context_object_name = 'profile_user'
    pk_url_kwarg = 'user_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object

        # Zliczanie punktów emocji z agregacją
        emotion_stats = profile_user.emotion_points.aggregate(
            total_count=Count('id'),
            public_count=Count('id', filter=Q(privacy_status='public')),
            private_count=Count('id', filter=Q(privacy_status='private'))
        )

        context['total_emotions'] = emotion_stats['total_count']
        context['public_emotions'] = emotion_stats['public_count']
        context['private_emotions'] = emotion_stats['private_count']

        # Ostatnie publiczne emocje z select_related dla lokalizacji
        context['recent_emotions'] = (
            profile_user.emotion_points
            .filter(privacy_status='public')
            .select_related('location')
            .order_by('-created_at')[:10]
        )

        # Czy przeglądający widzi swój własny profil
        context['is_own_profile'] = self.request.user.id == profile_user.id

        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile (own profile only)."""

    model = CFUser
    form_class = UserProfileEditForm
    template_name = 'auth/profile_edit.html'

    def get_object(self, queryset=None):
        # Zawsze edytujemy profil zalogowanego użytkownika
        return self.request.user

    def get_success_url(self):
        # Po zapisie wracamy na profil użytkownika
        return reverse_lazy('cf_auth:profile', kwargs={'user_id': self.request.user.id})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Twój profil został zaktualizowany.'
        )
        return response


class CommunityView(LoginRequiredMixin, ListView):
    """
    Widok społeczności - lista użytkowników z ich statystykami.
    Wyświetla tabelaryczny układ: użytkownik po lewej, szczegóły po prawej.
    """
    model = CFUser
    template_name = 'auth/community.html'
    context_object_name = 'users_list'
    paginate_by = 10

    def get_queryset(self):
        # Pobieramy tylko publiczne emocje do wyświetlenia w "ostatnich aktywnościach"
        public_emotions_qs = EmotionPoint.objects.filter(
            privacy_status='public'
        ).select_related('location').order_by('-created_at')

        # Główne zapytanie o użytkowników
        queryset = CFUser.objects.annotate(
            # Liczymy wszystkie emocje
            emotions_count=Count('emotion_points')
        ).prefetch_related(
            # Pobieramy 3 ostatnie publiczne emocje dla każdego usera
            Prefetch('emotion_points', queryset=public_emotions_qs, to_attr='recent_public_emotions')
        ).order_by('-date_joined')

        # Wyszukiwarka po username
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(username__icontains=search_query)

        return queryset