from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CFUser


class UserRegistrationForm(UserCreationForm):
    """Form for user registration with email field."""

    email = forms.EmailField(
        required=True,
        label='Email',
        help_text='Wymagany. Podaj prawidłowy adres email.'
    )

    class Meta:
        model = CFUser
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nazwa użytkownika',
        }
        help_texts = {
            'username': 'Wymagane. Maksymalnie 150 znaków. Tylko litery, cyfry oraz znaki @/./+/-/_',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nadpisz etykiety i help_text dla pól hasła
        self.fields['password1'].label = 'Hasło'
        self.fields['password1'].help_text = 'Hasło musi zawierać co najmniej 8 znaków i nie może być zbyt popularne.'
        self.fields['password2'].label = 'Potwierdź hasło'
        self.fields['password2'].help_text = 'Wpisz to samo hasło jeszcze raz w celu weryfikacji.'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
