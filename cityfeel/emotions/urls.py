from django.urls import path
from .views import EmotionPointListAPIView

urlpatterns = [
    path('emotion-points/', EmotionPointListAPIView.as_view(), name='emotion-points-list'),
]