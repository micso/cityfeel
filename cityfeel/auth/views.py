from django.contrib.auth import login
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages

from .forms import UserRegistrationForm


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
