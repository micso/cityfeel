from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from emotions.models import EmotionPoint
from map.models import Location

User = get_user_model()


class EmotionPointAPITestCase(TestCase):
    """Testy dla endpointu POST /api/emotion-points/"""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        # Utwórz użytkownika testowego
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Współrzędne testowe (Warszawa, Plac Zamkowy)
        self.test_lat = 52.2297
        self.test_lon = 21.0122

        # URL endpointu
        self.url = '/api/emotion-points/'

    def make_location_data(self, lat, lon, name=None):
        """Helper do tworzenia location data."""
        data = {
            'coordinates': {
                'latitude': lat,
                'longitude': lon,
            }
        }
        if name is not None:
            data['name'] = name
        return data

    def test_create_emotion_point_success(self):
        """Test tworzenia nowego EmotionPoint."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': {
                'coordinates': {
                    'latitude': self.test_lat,
                    'longitude': self.test_lon,
                },
            },
            'emotional_value': 4,
            'privacy_status': 'public'
        }

        response = self.client.post(self.url, data, format='json')

        # Sprawdź status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź dane odpowiedzi
        self.assertEqual(response.data['emotional_value'], 4)
        self.assertEqual(response.data['privacy_status'], 'public')
        self.assertEqual(response.data['location']['coordinates']['latitude'], self.test_lat)
        self.assertEqual(response.data['location']['coordinates']['longitude'], self.test_lon)

        # Sprawdź czy utworzono w bazie
        self.assertEqual(EmotionPoint.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)

        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.user, self.user)
        self.assertEqual(emotion_point.emotional_value, 4)

    def test_update_existing_emotion_point(self):
        """Test aktualizacji istniejącego EmotionPoint."""
        self.client.force_authenticate(user=self.user)

        # Utwórz początkowy punkt
        location = Location.objects.create(
            name='Test Location',
            coordinates=Point(self.test_lon, self.test_lat, srid=4326)
        )
        EmotionPoint.objects.create(
            user=self.user,
            location=location,
            emotional_value=3,
            privacy_status='public'
        )

        # Wyślij request z tymi samymi współrzędnymi
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 5,
            'privacy_status': 'private'
        }

        response = self.client.post(self.url, data, format='json')

        # Sprawdź status code (POST zawsze zwraca 201)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź zaktualizowane wartości
        self.assertEqual(response.data['emotional_value'], 5)
        self.assertEqual(response.data['privacy_status'], 'private')

        # Sprawdź że nie utworzono duplikatu
        self.assertEqual(EmotionPoint.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)

        # Sprawdź wartości w bazie
        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.emotional_value, 5)
        self.assertEqual(emotion_point.privacy_status, 'private')

    def test_proximity_matching_uses_nearby_location(self):
        """Test czy proximity matching używa istniejącej Location w promieniu."""
        self.client.force_authenticate(user=self.user)

        # Utwórz Location 30m od punktu testowego
        # Przesunięcie ~30m na północ (0.0003 stopnia ~ 30m)
        nearby_lat = self.test_lat + 0.0003
        nearby_point = Point(self.test_lon, nearby_lat, srid=4326)

        location = Location.objects.create(
            name='Nearby Location',
            coordinates=nearby_point
        )

        # Wyślij request z oryginalnym punktem
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź że nie utworzono nowej Location
        self.assertEqual(Location.objects.count(), 1)

        # Sprawdź że użyto istniejącej Location
        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.location, location)

    def test_proximity_matching_creates_new_location_if_far(self):
        """Test czy tworzy nową Location jeśli najbliższa jest poza promieniem."""
        self.client.force_authenticate(user=self.user)

        # Utwórz Location 100m od punktu testowego (poza domyślnym promieniem 50m)
        # 0.001 stopnia ~ 100m
        far_lat = self.test_lat + 0.001
        far_point = Point(self.test_lon, far_lat, srid=4326)

        Location.objects.create(
            name='Far Location',
            coordinates=far_point
        )

        # Wyślij request z oryginalnym punktem
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź że utworzono nową Location
        self.assertEqual(Location.objects.count(), 2)

    def test_default_privacy_status_is_public(self):
        """Test czy domyślny privacy_status to 'public'."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
            # Brak privacy_status
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['privacy_status'], 'public')

    def test_unauthenticated_request_fails(self):
        """Test czy nieautoryzowany request zwraca 401/403."""
        # NIE autentykuj użytkownika
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        # Może być 401 lub 403 w zależności od konfiguracji DRF
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_invalid_emotional_value_too_low(self):
        """Test walidacji: emotional_value < 1."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 0,  # Nieprawidłowe
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('emotional_value', response.data)

    def test_invalid_emotional_value_too_high(self):
        """Test walidacji: emotional_value > 5."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 6,  # Nieprawidłowe
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('emotional_value', response.data)

    def test_invalid_latitude_too_low(self):
        """Test walidacji: latitude < -90."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(-91.0, self.test_lon),  # Nieprawidłowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_latitude_too_high(self):
        """Test walidacji: latitude > 90."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(91.0, self.test_lon),  # Nieprawidłowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_longitude_too_low(self):
        """Test walidacji: longitude < -180."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, -181.0),  # Nieprawidłowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_longitude_too_high(self):
        """Test walidacji: longitude > 180."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, 181.0),  # Nieprawidłowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_privacy_status(self):
        """Test walidacji: nieprawidłowy privacy_status."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
            'privacy_status': 'invalid_status',  # Nieprawidłowe
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('privacy_status', response.data)

    def test_missing_required_field_latitude(self):
        """Test walidacji: brak wymaganego pola latitude."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': {
                'coordinates': {
                    # Brak latitude
                    'longitude': self.test_lon,
                }
            },
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_missing_required_field_longitude(self):
        """Test walidacji: brak wymaganego pola longitude."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': {
                'coordinates': {
                    'latitude': self.test_lat,
                    # Brak longitude
                }
            },
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_missing_required_field_emotional_value(self):
        """Test walidacji: brak wymaganego pola emotional_value."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            # Brak emotional_value
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('emotional_value', response.data)

    def test_edge_case_latitude_boundary_values(self):
        """Test wartości granicznych latitude (-90, 90)."""
        self.client.force_authenticate(user=self.user)

        # Test -90 (South Pole)
        data = {
            'location': self.make_location_data(-90.0, self.test_lon),
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test 90 (North Pole)
        data = {
            'location': self.make_location_data(90.0, 0.0),  # Zmieniona longitude żeby był nowy punkt
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edge_case_longitude_boundary_values(self):
        """Test wartości granicznych longitude (-180, 180)."""
        self.client.force_authenticate(user=self.user)

        # Test -180
        data = {
            'location': self.make_location_data(0.0, -180.0),
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test 180
        data = {
            'location': self.make_location_data(10.0, 180.0),  # Zmieniona latitude żeby był nowy punkt
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_multiple_users_same_location(self):
        """Test: różni użytkownicy mogą dodać EmotionPoint na tej samej Location."""
        self.client.force_authenticate(user=self.user)

        # Pierwszy użytkownik dodaje punkt
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }
        response1 = self.client.post(self.url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Drugi użytkownik
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=user2)

        # Drugi użytkownik dodaje punkt na tej samej Location
        response2 = self.client.post(self.url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Sprawdź że są 2 EmotionPointy
        self.assertEqual(EmotionPoint.objects.count(), 2)
        # Ale tylko 1 Location
        self.assertEqual(Location.objects.count(), 1)

    def test_response_contains_all_required_fields(self):
        """Test czy odpowiedź zawiera wszystkie wymagane pola."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
            'privacy_status': 'public',
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź obecność wszystkich pól top-level
        required_fields = [
            'id',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
        ]

        for field in required_fields:
            self.assertIn(field, response.data, f"Brak pola '{field}' w odpowiedzi")

        # Sprawdź obecność pól w nested location
        location_fields = ['id', 'name', 'coordinates']
        for field in location_fields:
            self.assertIn(field, response.data['location'], f"Brak pola '{field}' w location")

        # Sprawdź obecność pól w nested coordinates
        coordinates_fields = ['latitude', 'longitude']
        for field in coordinates_fields:
            self.assertIn(field, response.data['location']['coordinates'], f"Brak pola '{field}' w coordinates")

    def test_location_name_is_auto_generated(self):
        """Test czy nazwa Location jest automatycznie generowana w formacie 'Lat: XX.XXXX, Lon: YY.YYYY'."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(52.2297, 21.0122),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź format nazwy lokalizacji
        expected_name = "Lat: 52.2297, Lon: 21.0122"
        self.assertEqual(response.data['location']['name'], expected_name)

        # Sprawdź że Location w bazie ma tę samą nazwę
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, expected_name)

    def test_custom_location_name(self):
        """Test czy można podać własną nazwę lokalizacji."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Plac Zamkowy"
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, custom_name),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź czy użyto podanej nazwy
        self.assertEqual(response.data['location']['name'], custom_name)

        # Sprawdź że Location w bazie ma tę nazwę
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, custom_name)

    def test_custom_location_name_overrides_auto_generation(self):
        """Test czy własna nazwa ma pierwszeństwo przed auto-generowaną."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Moja ulubiona kawiarnia"
        data = {
            'location': self.make_location_data(50.0614, 19.9366, custom_name),
            'emotional_value': 5,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdź że nie została użyta auto-generowana nazwa
        self.assertNotEqual(response.data['location']['name'], "Lat: 50.0614, Lon: 19.9366")
        # Sprawdź że użyto nazwy podanej przez użytkownika
        self.assertEqual(response.data['location']['name'], custom_name)

    def test_location_name_max_length_validation(self):
        """Test walidacji: location_name dłuższa niż 200 znaków."""
        self.client.force_authenticate(user=self.user)

        # Nazwa 201 znaków (za długa)
        long_name = "A" * 201
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, long_name),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_location_name_empty_string_validation(self):
        """Test walidacji: location_name jako pusty string."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, ''),  # Pusty string
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_location_name_with_special_characters(self):
        """Test czy nazwa lokalizacji może zawierać znaki specjalne i polskie znaki."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Kawiarnia \"Pod Aniołem\" - ul. Świętokrzyska 10/12"
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, custom_name),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['location']['name'], custom_name)

        # Sprawdź w bazie
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, custom_name)
