from django_filters import rest_framework as filters
from django.contrib.gis.geos import Point, Polygon
from map.models import Location
from emotions.models import EmotionPoint

class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass

class LocationFilter(filters.FilterSet):
    """
    Custom FilterSet dla Location z obsługą GIS queries.

    Filtry:
    - name: filtrowanie po nazwie (case-insensitive contains)
    - lat, lon, radius: filtrowanie po promieniu (radius w metrach)
    - bbox: filtrowanie po bounding box (format: lon_min,lat_min,lon_max,lat_max)
    """

    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    emotional_value = filters.BaseInFilter(field_name='emotion_points__emotional_value')

    # Filtry dla radius search
    lat = filters.NumberFilter(method='filter_radius')
    lon = filters.NumberFilter(method='filter_radius')
    radius = filters.NumberFilter(method='filter_radius')

    # Filter dla bounding box
    bbox = filters.CharFilter(method='filter_bbox')

    class Meta:
        model = Location
        fields = ['name', 'lat', 'lon', 'radius', 'bbox', 'emotional_value']

    def filter_radius(self, queryset, name, value):
        """
        Filtruje lokalizacje w promieniu od punktu (lat, lon).
        Wymaga wszystkich trzech parametrów: lat, lon, radius.
        Radius w metrach.
        """
        request = self.request
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = request.query_params.get('radius')

        # Walidacja: wszystkie parametry muszą być obecne
        if not (lat and lon and radius):
            return queryset

        try:
            lat = float(lat)
            lon = float(lon)
            radius_meters = float(radius)
        except (ValueError, TypeError):
            return queryset.none()

        # Walidacja zakresu
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return queryset.none()

        if radius_meters <= 0:
            return queryset.none()

        # Utwórz punkt i filtruj
        point = Point(lon, lat, srid=4326)

        # Konwertuj metry na stopnie (przybliżenie)
        # 1 stopień szerokości geograficznej ≈ 111320 metrów
        # Dla SRID 4326 (geographic) używamy stopni zamiast D(m=...)
        radius_degrees = radius_meters / 111320.0

        return queryset.filter(coordinates__dwithin=(point, radius_degrees))

    def filter_bbox(self, queryset, name, value):
        """
        Filtruje lokalizacje w bounding box.
        Format: lon_min,lat_min,lon_max,lat_max
        Przykład: ?bbox=18.5,54.3,18.7,54.4
        """
        try:
            coords = [float(x) for x in value.split(',')]

            if len(coords) != 4:
                return queryset.none()

            lon_min, lat_min, lon_max, lat_max = coords

            # Walidacja zakresów
            if not (-180 <= lon_min <= 180) or not (-180 <= lon_max <= 180):
                return queryset.none()
            if not (-90 <= lat_min <= 90) or not (-90 <= lat_max <= 90):
                return queryset.none()

            # Utwórz Polygon dla bounding box
            bbox_polygon = Polygon.from_bbox((lon_min, lat_min, lon_max, lat_max))
            return queryset.filter(coordinates__contained=bbox_polygon)

        except (ValueError, AttributeError):
            return queryset.none()


class EmotionPointFilter(filters.FilterSet):
    """
    Custom FilterSet dla EmotionPoint.

    Filtry:
    - emotional_value: filtrowanie po wielu wartościach (np. ?emotional_value=1,2,3)
    """

    emotional_value = NumberInFilter(field_name='emotional_value', lookup_expr='in')

    class Meta:
        model = EmotionPoint
        fields = ['emotional_value']
