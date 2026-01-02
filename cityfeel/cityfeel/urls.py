from django.contrib import admin
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static
from map.views import location_detail

urlpatterns = [
    path('admin/', admin.site.urls),

    # Twoje stare API do lokalizacji
    path('api/locations/<int:id>/', location_detail, name='location_detail'),

    # --- NOWE: Podpinamy ca³e API emocji (punkty, komentarze, zdjêcia) ---
    path('api/emotions/', include('emotions.urls')),
]

# Obs³uga zdjêæ (¿eby siê wyœwietla³y w przegl¹darce)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)