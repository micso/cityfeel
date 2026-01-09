from django import forms
from .models import Photo

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        # [ZMIANA] Dodano privacy_status do fields
        fields = ['image', 'caption', 'privacy_status']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opis zdjęcia (opcjonalny)'}),
            'privacy_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'image': 'Wybierz plik',
            'caption': 'Podpis',
            'privacy_status': 'Prywatność',
        }