from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Friendship


class FriendsPageView(LoginRequiredMixin, TemplateView):
    """
    Widok renderujący stronę HTML z listą znajomych i zaproszeniami.
    """
    template_name = 'social/friends.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # 1. Pobierz oczekujące zaproszenia (gdzie user jest celem)
        context['pending_requests'] = Friendship.objects.filter(
            target=user,
            status='pending'
        ).select_related('creator')

        # 2. Pobierz zaakceptowane relacje (obiekty Friendship), aby mieć dostęp do ID relacji do usuwania
        context['friendships'] = Friendship.objects.filter(
            (Q(creator=user) | Q(target=user)) & Q(status='accepted')
        ).select_related('creator', 'target')

        return context