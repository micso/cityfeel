from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmotionPointViewSet, CommentViewSet, PhotoViewSet


router = DefaultRouter()
router.register(r'points', EmotionPointViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'photos', PhotoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]