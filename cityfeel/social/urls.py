from django.urls import path
from .views import FriendsPageView

app_name = 'social'

urlpatterns = [
    path('my-friends/', FriendsPageView.as_view(), name='friends_page'),
]