from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers
from . import views

# Importujemy FriendshipViewSet i FriendListView bezpośrednio z .views (api/views.py)
from .views import FriendshipViewSet, FriendListView

app_name = 'api'

router = routers.SimpleRouter()
router.register('emotion-points', views.EmotionPointViewSet, basename='emotion_points')
router.register('locations', views.LocationViewSet, basename='locations')
# Rejestracja Friendship ViewSet (obsługuje POST /, PATCH /{id}/, GET /requests/, DELETE /{id}/)
router.register('friendship', FriendshipViewSet, basename='friendship')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),

    # Endpoint dla listy znajomych (osobny widok GenericAPIView)
    path('friends/', FriendListView.as_view(), name='friends-list'),
]

urlpatterns = urlpatterns + router.urls