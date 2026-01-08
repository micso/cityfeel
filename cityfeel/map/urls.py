from django.urls import path
from .views import EmotionMapView, LocationDetailView

app_name = 'map'

urlpatterns = [
    path('', EmotionMapView.as_view(), name='emotion_map'),
    path('location/<int:pk>/', LocationDetailView.as_view(), name='location_detail'),
]
