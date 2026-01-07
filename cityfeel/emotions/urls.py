from django.urls import path
from . import views

app_name = 'emotions'

urlpatterns = [
    path('delete/<int:pk>/', views.delete_emotion, name='delete'),
]