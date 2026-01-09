from django import forms
from .models import Comment, Photo  # Import obu modeli

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
                'placeholder': 'Napisz komentarz...'
            })
        }
        labels = {
            'content': ''
        }

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