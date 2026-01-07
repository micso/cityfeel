from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers
from . import views

app_name = 'api'

router = routers.SimpleRouter()
router.register('emotion-points', views.EmotionPointViewSet, basename='emotion_points')
router.register('locations', views.LocationViewSet, basename='locations')
router.register('friendship', views.FriendshipViewSet, basename='friendship')
router.register('comments', views.CommentViewSet, basename='comments')

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),

    # Custom endpoint alias dla listy znajomych
    path('friends/', views.FriendshipViewSet.as_view({'get': 'friends_list'}), name='friends-list'),
]

urlpatterns = urlpatterns + router.urls