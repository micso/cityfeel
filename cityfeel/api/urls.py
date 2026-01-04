from rest_framework import routers
from . import views

app_name = 'api'

router = routers.SimpleRouter()
router.register('emotion-points', views.EmotionPointViewSet, basename='emotion_points')

urlpatterns = router.urls
