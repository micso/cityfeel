from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path(
        'emotion-points/',
        views.EmotionPointCreateView.as_view(),
        name='emotion_point_create'
    ),
]
