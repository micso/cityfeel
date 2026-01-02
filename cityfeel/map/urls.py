from django.urls import path
from .views import EmotionMapView

app_name = 'map'

urlpatterns = [
    path('', EmotionMapView.as_view(), name='emotion_map'),
]
