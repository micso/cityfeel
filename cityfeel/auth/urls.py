from django.urls import path
from django.contrib.auth import views as auth_views

from .views import RegisterView, UserProfileView, UserProfileEditView

app_name = 'cf_auth'

urlpatterns = [
    # Registration
    path('register/', RegisterView.as_view(), name='register'),

    # Login/Logout - Django built-in views
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # User Profile
    path('user/<int:user_id>/', UserProfileView.as_view(), name='profile'),
    path('user/edit/', UserProfileEditView.as_view(), name='profile_edit'),
]
