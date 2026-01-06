from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers
from . import views

# Import widoków z nowej aplikacji social
from social.views import FriendshipViewSet, FriendListView

app_name = 'api'

router = routers.SimpleRouter()
router.register('emotion-points', views.EmotionPointViewSet, basename='emotion_points')
router.register('locations', views.LocationViewSet, basename='locations')

# Rejestracja endpointu /api/friendship/
router.register('friendship', FriendshipViewSet, basename='friendship')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),

    # Rejestracja endpointu /api/friends/
    path('friends/', FriendListView.as_view(), name='friends-list'),
]

urlpatterns = urlpatterns + router.urls