from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Importujemy Twój gotowy widok z pliku views.py
from map.views import location_detail

urlpatterns = [
    path('admin/', admin.site.urls),

    # Tutaj podpinamy adres API pod Twoj¹ funkcjê
    path('api/locations/<int:id>/', location_detail, name='location_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)