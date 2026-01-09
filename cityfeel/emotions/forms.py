from django import forms
from .models import Photo

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Krótki opis zdjęcia'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'image': 'Zdjęcie (max 5MB)',
            'caption': 'Opis',
        }