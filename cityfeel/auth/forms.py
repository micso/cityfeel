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


class UserProfileEditForm(forms.ModelForm):
    """Form for editing user profile."""

    email = forms.EmailField(
        required=True,
        label='Email',
        help_text='Wymagany. Podaj prawidłowy adres email.',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    first_name = forms.CharField(
        required=False,
        max_length=150,
        label='Imię',
        help_text='Opcjonalne.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    last_name = forms.CharField(
        required=False,
        max_length=150,
        label='Nazwisko',
        help_text='Opcjonalne.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    description = forms.CharField(
        required=False,
        max_length=500,
        label='Opis',
        help_text='Opcjonalne. Maksymalnie 500 znaków.',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Opowiedz coś o sobie...'
        })
    )

    avatar = forms.ImageField(
        required=False,
        label='Zdjęcie profilowe',
        help_text='Opcjonalne. Maksymalnie 5MB. Formaty: JPG, PNG.',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CFUser
        fields = ['first_name', 'last_name', 'email', 'description', 'avatar']

    def clean_email(self):
        """Validate that email is unique (excluding current user)."""
        email = self.cleaned_data.get('email')
        if email:
            # Sprawdź czy email nie jest już używany przez innego użytkownika
            existing = CFUser.objects.filter(email=email).exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('Ten adres email jest już używany.')
        return email

    def clean_avatar(self):
        """Validate avatar file size and format."""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Sprawdź rozmiar pliku (5MB = 5242880 bytes)
            if avatar.size > 5242880:
                raise forms.ValidationError('Plik jest zbyt duży. Maksymalny rozmiar to 5MB.')

            # Sprawdź rozszerzenie
            import os
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError('Niedozwolony format pliku. Dozwolone: JPG, PNG.')

        return avatar
