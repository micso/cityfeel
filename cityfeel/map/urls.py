from django.urls import path
from .views import EmotionMapView, LocationDetailView
from . import views

app_name = 'map'

urlpatterns = [
    path('', views.EmotionMapView.as_view(), name='emotion_map'),
    path('lista/', views.LocationListView.as_view(), name='location_list'),
    path('location/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
]
