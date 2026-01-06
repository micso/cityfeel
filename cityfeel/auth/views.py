from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, UpdateView, ListView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Q, Prefetch

from emotions.models import EmotionPoint
from social.models import Friendship
from .forms import UserRegistrationForm, UserProfileEditForm
from .models import CFUser


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


class CommunityView(ListView):
    """
    Widok społeczności / lista użytkowników.
    Wyświetla listę użytkowników, ich statystyki, ostatnią aktywność i status relacji.
    """
    model = CFUser
    template_name = 'auth/community.html'
    context_object_name = 'users'
    paginate_by = 10  # Paginacja co 10 użytkowników

    def get_queryset(self):
        # Pobieramy tylko aktywnych użytkowników
        queryset = CFUser.objects.filter(is_active=True)

        # 1. Wyszukiwanie po username (jeśli podano parametr 'q')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(username__icontains=query)

        # 2. Optymalizacja zapytania o ostatnie oceny (publiczne)
        # Pobieramy oceny publiczne, posortowane od najnowszych, wraz z lokalizacją
        recent_emotions_qs = EmotionPoint.objects.filter(
            privacy_status='public'
        ).select_related('location').order_by('-created_at')

        # 3. Annotacja (liczba ocen) i Prefetch (ostatnie oceny)
        queryset = queryset.annotate(
            ratings_count=Count('emotion_points')
        ).prefetch_related(
            Prefetch('emotion_points', queryset=recent_emotions_qs, to_attr='public_ratings')
        ).order_by('-ratings_count')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')

        # Logika sprawdzania relacji
        if self.request.user.is_authenticated:
            # Pobieramy listę użytkowników z obecnej strony paginacji
            page_users = context['object_list'] if 'object_list' in context else context['users']

            # Pobierz ID wyświetlanych użytkowników
            page_user_ids = [u.id for u in page_users]

            # Pobierz relacje gdzie user jest twórcą LUB celem, a druga strona jest na liście
            friendships = Friendship.objects.filter(
                (Q(creator=self.request.user) & Q(target_id__in=page_user_ids)) |
                (Q(target=self.request.user) & Q(creator_id__in=page_user_ids))
            )

            # Stwórz mapę {user_id: friendship_object}
            friendship_map = {}
            for f in friendships:
                # Jeśli ja stworzyłem, to kluczem jest target, jeśli ja jestem targetem, kluczem jest creator
                other_id = f.target_id if f.creator_id == self.request.user.id else f.creator_id
                friendship_map[other_id] = f

            # Przypisz obiekt relacji do użytkownika w liście (tylko na potrzeby wyświetlania)
            for u in page_users:
                u.friendship_status = friendship_map.get(u.id)

        return context