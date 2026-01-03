from django.urls import path
from .views import EmotionPointListAPIView

app_name = 'api'

urlpatterns = [
    path('emotion-points/', EmotionPointListAPIView.as_view(), name='emotion-point-list'),
]