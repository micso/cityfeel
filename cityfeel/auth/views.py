from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, UpdateView, ListView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Q, Prefetch

from .forms import UserRegistrationForm, UserProfileEditForm
from .models import CFUser, Friendship
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
    Widok społeczności - lista użytkowników z ich statystykami i statusem znajomości.
    Wyświetla tabelaryczny układ: użytkownik po lewej, szczegóły po prawej.
    """
    model = CFUser
    template_name = 'auth/community.html'
    context_object_name = 'users_list'
    paginate_by = 10

    def get_queryset(self):
        current_user = self.request.user

        # Pobieramy tylko publiczne emocje do wyświetlenia w "ostatnich aktywnościach"
        public_emotions_qs = EmotionPoint.objects.filter(
            privacy_status='public'
        ).select_related('location').order_by('-created_at')

        # Wykluczamy zalogowanego użytkownika z listy
        queryset = CFUser.objects.exclude(id=current_user.id).annotate(
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users_list = context['users_list']
        current_user = self.request.user

        # Pobierz wszystkie relacje, gdzie userem jest current_user
        # Tworzymy mapę {other_user_id: friendship_object}
        friendships_map = {}

        # Pobierz relacje gdzie current_user jest senderem lub receiverem
        friendships = Friendship.objects.filter(
            Q(user=current_user) | Q(friend=current_user)
        )

        for f in friendships:
            if f.user == current_user:
                other_id = f.friend.id
                direction = 'sent'  # current_user wysłał zaproszenie
            else:
                other_id = f.user.id
                direction = 'received'  # current_user otrzymał zaproszenie

            friendships_map[other_id] = {
                'obj': f,
                'status': f.status,
                'direction': direction,
                'id': f.id,
                'created_at': f.created_at
            }

        # Wstrzyknij status znajomości do obiektów użytkowników na liście
        for user in users_list:
            if user.id in friendships_map:
                data = friendships_map[user.id]
                user.friendship_status = data['status']  # 'pending' or 'accepted'
                user.friendship_direction = data['direction']  # 'sent' or 'received'
                user.friendship_id = data['id']
                user.friendship_created_at = data['created_at']
            else:
                user.friendship_status = None

        return context


class MyFriendsView(LoginRequiredMixin, TemplateView):
    """
    Widok 'Moi znajomi' - wyświetla oczekujące zaproszenia i listę znajomych.
    """
    template_name = 'auth/my_friends.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Oczekujące zaproszenia (Otrzymane) - gdzie current user jest 'friend' i status 'pending'
        pending_requests = Friendship.objects.filter(
            friend=user,
            status=Friendship.PENDING
        ).select_related('user').order_by('-created_at')

        context['pending_requests'] = pending_requests

        # 2. Lista znajomych (Zaakceptowane)
        accepted_friendships = Friendship.objects.filter(
            (Q(user=user) | Q(friend=user)) & Q(status=Friendship.ACCEPTED)
        ).select_related('user', 'friend').order_by('created_at')

        friends_list = []
        for f in accepted_friendships:
            # Ustal, kto jest tym 'drugim'
            friend_user = f.friend if f.user == user else f.user

            # Dodajmy ID relacji, żeby można było ją usunąć
            friend_user.friendship_id = f.id
            friend_user.friendship_since = f.created_at
            friends_list.append(friend_user)

        context['friends_list'] = friends_list

        return context
