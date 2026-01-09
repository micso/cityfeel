from django.urls import path
from . import views

app_name = 'emotions'

urlpatterns = [
    path('delete/emotion/<int:pk>/', views.delete_emotion, name='delete_emotion'),
    path('delete/comment/<int:pk>/', views.delete_comment, name='delete_comment'),
    path('delete/photo/<int:pk>/', views.delete_photo, name='delete_photo'),
    # [NOWE]
    path('edit/photo/<int:pk>/', views.edit_photo_caption, name='edit_photo_caption'),
]