from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CFUser


class UserRegistrationForm(UserCreationForm):
    """Form for user registration with email field."""

    email = forms.EmailField(
        required=True,
        help_text='Wymagany. Podaj prawidłowy adres email.'
    )

    class Meta:
        model = CFUser
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
