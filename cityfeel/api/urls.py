from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers
from . import views

app_name = 'api'

router = routers.SimpleRouter()
router.register('emotion-points', views.EmotionPointViewSet, basename='emotion_points')
router.register('locations', views.LocationViewSet, basename='locations')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]

urlpatterns = urlpatterns + router.urls