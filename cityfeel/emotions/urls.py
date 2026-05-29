from django.urls import path
from . import views
from . import dashboard_views

app_name = 'emotions'

urlpatterns = [
    path('dashboard/', dashboard_views.city_statistics_dashboard, name='city_dashboard'),
    path('delete/emotion/<int:pk>/', views.delete_emotion, name='delete_emotion'),
    path('delete/comment/<int:pk>/', views.delete_comment, name='delete_comment'),
    path('delete/photo/<int:pk>/', views.delete_photo, name='delete_photo'),
    path('edit/photo/<int:pk>/', views.edit_photo_caption, name='edit_photo_caption'),
    path('moderation/reports/', views.admin_reports_view, name='admin_reports'),
]