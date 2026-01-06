from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from django.db.models import Q

from emotions.models import EmotionPoint
from map.models import Location
from auth.models import Friendship, CFUser


@extend_schema_field({
    'type': 'object',
    'properties': {
        'latitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -90.0,
            'maximum': 90.0,
            'description': 'Szerokość geograficzna'
        },
        'longitude': {
            'type': 'number',
            'format': 'float',
            'minimum': -180.0,
            'maximum': 180.0,
            'description': 'Długość geograficzna'
        }
    },
    'required': ['latitude', 'longitude'],
    'example': {
        'latitude': 54.3520,
        'longitude': 18.6466
    }
})
class PointField(serializers.Field):
    """
    Custom serializer field dla django.contrib.gis.db.models.fields.PointField.

    Konwertuje PostGIS Point na format {latitude, longitude} i odwrotnie.
    """

    def to_representation(self, value):
        """Konwertuje PostGIS Point na dict {latitude, longitude}."""
        if value is None:
            return None

        return {
            'latitude': value.y,
            'longitude': value.x,
        }

    def to_internal_value(self, data):
        """Konwertuje dict {latitude, longitude} na PostGIS Point."""
        if not isinstance(data, dict):
            raise serializers.ValidationError("Współrzędne muszą być w formacie obiektu.")

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        # Walidacja latitude
        if latitude is None:
            raise serializers.ValidationError({'latitude': 'Pole latitude jest wymagane.'})

        try:
            latitude = float(latitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'latitude': 'Nieprawidłowy format szerokości geograficznej.'})

        if latitude < -90.0 or latitude > 90.0:
            raise serializers.ValidationError({'latitude': 'Szerokość geograficzna musi być w zakresie -90 do 90.'})

        # Walidacja longitude
        if longitude is None:
            raise serializers.ValidationError({'longitude': 'Pole longitude jest wymagane.'})

        try:
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise serializers.ValidationError({'longitude': 'Nieprawidłowy format długości geograficznej.'})

        if longitude < -180.0 or longitude > 180.0:
            raise serializers.ValidationError({'longitude': 'Długość geograficzna musi być w zakresie -180 do 180.'})

        # Utwórz PostGIS Point (longitude FIRST, latitude SECOND - standard WGS84)
        return Point(longitude, latitude, srid=4326)


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer dla modelu Location z obsługą PostGIS Point.
    Używa custom PointField do konwersji współrzędnych.
    Może być używany samodzielnie w przyszłych endpointach.
    """
    coordinates = PointField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates']
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {
                'required': False,  # Opcjonalne, będzie auto-generowane
                'allow_blank': False,
                'max_length': 200,
                'error_messages': {
                    'max_length': 'Nazwa lokalizacji nie może być dłuższa niż 200 znaków.',
                    'blank': 'Nazwa lokalizacji nie może być pusta.',
                }
            }
        }


class LocationListSerializer(serializers.ModelSerializer):
    """
    Serializer dla endpointu GET /api/locations/ z dodatkowym polem avg_emotional_value.
    Używany do wyświetlania listy lokalizacji z agregowanymi danymi emocji.

    avg_emotional_value liczy średnią ze WSZYSTKICH emotion-points (publicznych i prywatnych).
    Privacy status kontroluje tylko widoczność kto jak ocenił, nie wpływa na średnią.
    """
    coordinates = PointField()
    avg_emotional_value = serializers.SerializerMethodField()
    emotion_points_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']
        read_only_fields = ['id', 'name', 'coordinates', 'avg_emotional_value', 'emotion_points_count']

    @extend_schema_field({
        'type': 'number',
        'format': 'float',
        'nullable': True,
        'description': 'Średnia wartość emocjonalna (1-5) dla tej lokalizacji. '
                       'Liczy ze wszystkich emotion-points (publicznych i prywatnych). '
                       'Null jeśli lokalizacja nie ma żadnych emotion-points.',
        'example': 4.2
    })
    def get_avg_emotional_value(self, obj):
        """
        Zwraca średnią wartość emocjonalną dla tej lokalizacji.
        Używa annotacji z queryset jeśli dostępna, inaczej None.
        """
        # Wartość będzie dostępna przez annotate() w viewset queryset
        return getattr(obj, 'avg_emotional_value', None)


class EmotionPointSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    location = LocationSerializer()

    class Meta:
        model = EmotionPoint
        fields = [
            'id',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'emotional_value': {
                'error_messages': {
                    'min_value': 'Wartość emocjonalna musi być w zakresie 1-5.',
                    'max_value': 'Wartość emocjonalna musi być w zakresie 1-5.',
                    'required': 'Pole emotional_value jest wymagane.',
                    'invalid': 'Nieprawidłowy format wartości emocjonalnej.',
                }
            },
            'privacy_status': {
                'error_messages': {
                    'invalid_choice': 'Status prywatności musi być "public" lub "private".',
                }
            }
        }

    def create(self, validated_data):
        """
        Tworzy lub aktualizuje EmotionPoint z proximity matching dla Location.

        Logika:
        1. Wyciągnij nested location data z validated_data
        2. Wyciągnij coordinates (PostGIS Point) i name z location data
        3. Użyj proximity matching aby znaleźć lub utworzyć Location
        4. Sprawdź czy użytkownik ma już EmotionPoint dla tej Location
        5. Jeśli tak - zaktualizuj, jeśli nie - utwórz nowy
        """
        # Wyciągnij nested location data
        location_data = validated_data.pop('location')
        point = location_data['coordinates']  # PostGIS Point z PointField
        custom_location_name = location_data.get('name', None)

        user = self.context['request'].user

        # Pobierz promień z settings
        proximity_radius_meters = getattr(
            settings,
            'CITYFEEL_LOCATION_PROXIMITY_RADIUS',
            50  # domyślnie 50 metrów
        )

        # Konwertuj metry na stopnie (przybliżenie)
        # 1 stopień szerokości geograficznej ≈ 111320 metrów
        proximity_radius_degrees = proximity_radius_meters / 111320.0

        # Proximity matching: znajdź najbliższą Location w promieniu
        # Używamy dwithin z wartością w stopniach dla SRID 4326
        nearby_location = (
            Location.objects
            .filter(coordinates__dwithin=(point, proximity_radius_degrees))
            .annotate(distance=Distance('coordinates', point))
            .order_by('distance')
            .first()
        )

        if nearby_location:
            # Użyj istniejącej lokalizacji
            location = nearby_location
        else:
            # Utwórz nową lokalizację
            # Użyj nazwy podanej przez użytkownika lub wygeneruj automatycznie
            if custom_location_name:
                location_name = custom_location_name
            else:
                # Nazwa lokalizacji: "Lat: XX.XXXX, Lon: YY.YYYY"
                location_name = f"Lat: {point.y:.4f}, Lon: {point.x:.4f}"

            location = Location.objects.create(
                name=location_name,
                coordinates=point
            )

        # Sprawdź czy użytkownik już ma EmotionPoint dla tej Location
        try:
            emotion_point = EmotionPoint.objects.get(user=user, location=location)

            # Aktualizuj istniejący punkt
            emotion_point.emotional_value = validated_data.get(
                'emotional_value',
                emotion_point.emotional_value
            )
            emotion_point.privacy_status = validated_data.get(
                'privacy_status',
                emotion_point.privacy_status
            )
            emotion_point.save()

        except EmotionPoint.DoesNotExist:
            # Utwórz nowy punkt
            emotion_point = EmotionPoint.objects.create(
                user=user,
                location=location,
                **validated_data
            )

        return emotion_point


class FriendshipSerializer(serializers.ModelSerializer):
    """
    Serializer dla modelu Friendship (zaproszenia do znajomych).
    """
    friend_id = serializers.PrimaryKeyRelatedField(
        source='friend',
        queryset=CFUser.objects.all(),
        write_only=True
    )
    user = serializers.StringRelatedField(read_only=True)
    friend = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Friendship
        fields = ['id', 'user', 'friend', 'friend_id', 'status', 'created_at']
        # Usunąłem 'status' z read_only_fields, aby umożliwić jego edycję (akceptację)
        read_only_fields = ['id', 'user', 'friend', 'created_at']

    def validate(self, attrs):
        """
        Walidacja:
        1. Nie można zaprosić samego siebie.
        2. Nie można zaprosić jeśli relacja już istnieje (w dowolną stronę).
        """
        request = self.context['request']

        # Walidacja przy tworzeniu (POST) - friend_id jest wymagane
        if self.instance is None:
            friend = attrs['friend']
            user = request.user

            if user == friend:
                raise serializers.ValidationError("Nie możesz wysłać zaproszenia do samego siebie.")

            # Sprawdź czy relacja już istnieje (w dowolnym kierunku)
            # (A->B) lub (B->A)
            existing = Friendship.objects.filter(
                (Q(user=user) & Q(friend=friend)) |
                (Q(user=friend) & Q(friend=user))
            ).exists()

            if existing:
                raise serializers.ValidationError(
                    "Relacja z tym użytkownikiem już istnieje (oczekująca lub zaakceptowana).")

        return attrs

    def create(self, validated_data):
        # Ustaw zalogowanego użytkownika jako wysyłającego
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FriendUserSerializer(serializers.ModelSerializer):
    """
    Serializer do wyświetlania użytkownika na liście znajomych.
    """
    friendship_id = serializers.IntegerField(read_only=True)
    friendship_since = serializers.DateTimeField(read_only=True)

    class Meta:
        model = CFUser
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'friendship_id', 'friendship_since']