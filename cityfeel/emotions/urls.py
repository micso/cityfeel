from django.urls import path
from . import views

app_name = 'emotions'

urlpatterns = [
    path('delete/<int:pk>/', views.delete_emotion, name='delete'),
    path('comment/add/<int:emotion_id>/', views.add_comment, name='add_comment'),
    # Nowy URL do usuwania komentarzy #
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
]