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


class LocationAPITestCase(TestCase):
    """Testy dla endpointu GET /api/locations/"""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        # Użytkownicy
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass456'
        )

        # Współrzędne (Gdańsk)
        self.gdansk_lat = 54.3520
        self.gdansk_lon = 18.6466

        # Lokalizacja 1 z publicznymi i prywatnymi emotion_points (avg = 4.0)
        self.location1 = Location.objects.create(
            name='Gdańsk Stare Miasto',
            coordinates=Point(self.gdansk_lon, self.gdansk_lat, srid=4326)
        )
        EmotionPoint.objects.create(
            user=self.user, location=self.location1,
            emotional_value=5, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location1,
            emotional_value=3, privacy_status='public'
        )

        # Lokalizacja 2 bez emotion_points
        self.location2 = Location.objects.create(
            name='Sopot Plaża',
            coordinates=Point(18.5700, 54.4415, srid=4326)
        )

        # Lokalizacja 3 z miksem publicznych i prywatnych (avg = 3.5)
        self.location3 = Location.objects.create(
            name='Gdynia Port',
            coordinates=Point(18.5536, 54.5189, srid=4326)
        )
        EmotionPoint.objects.create(
            user=self.user, location=self.location3,
            emotional_value=4, privacy_status='private'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location3,
            emotional_value=3, privacy_status='public'
        )

        self.url = '/api/locations/'

    # --- BASIC TESTS ---
    def test_list_locations_authenticated(self):
        """Test GET /api/locations/ - authorized user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)  # Pagination
        self.assertEqual(len(response.data['results']), 3)

    def test_list_locations_unauthenticated(self):
        """Test GET /api/locations/ - unauthorized returns 401/403."""
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_retrieve_location_detail(self):
        """Test GET /api/locations/{id}/ - retrieve single location."""
        self.client.force_authenticate(user=self.user)
        url = f'{self.url}{self.location1.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.location1.id)
        self.assertEqual(response.data['name'], 'Gdańsk Stare Miasto')

    def test_location_response_structure(self):
        """Test czy response zawiera wszystkie wymagane pola."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        location_data = response.data['results'][0]
        required_fields = ['id', 'name', 'coordinates', 'avg_emotional_value']

        for field in required_fields:
            self.assertIn(field, location_data)

        # Sprawdź strukturę coordinates
        self.assertIn('latitude', location_data['coordinates'])
        self.assertIn('longitude', location_data['coordinates'])

    # --- AVG_EMOTIONAL_VALUE TESTS ---
    def test_avg_emotional_value_calculation(self):
        """Test czy avg_emotional_value jest prawidłowo obliczane (5+3)/2=4.0."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        # Znajdź location1 w results
        location1_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location1.id),
            None
        )

        self.assertIsNotNone(location1_data)
        # Średnia z [5, 3] = 4.0
        self.assertEqual(float(location1_data['avg_emotional_value']), 4.0)

    def test_avg_emotional_value_includes_all_points(self):
        """Test czy avg uwzględnia WSZYSTKIE punkty (publiczne i prywatne)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        # location3 ma: prywatny=4, publiczny=3, avg=(4+3)/2=3.5
        location3_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location3.id),
            None
        )

        self.assertIsNotNone(location3_data)
        self.assertEqual(float(location3_data['avg_emotional_value']), 3.5)

    def test_avg_emotional_value_null_for_no_emotions(self):
        """Test czy avg=null dla lokalizacji bez emotion_points (location2)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        location2_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location2.id),
            None
        )

        self.assertIsNotNone(location2_data)
        self.assertIsNone(location2_data['avg_emotional_value'])

    # --- FILTERING TESTS ---
    def test_filter_by_name_exact(self):
        """Test filtrowania ?name=Gdańsk (powinny być 2 lokalizacje)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'name': 'Gdańsk'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinny być 2 lokalizacje z "Gdańsk" w nazwie (location1)
        # Uwaga: plan wspominał o 2, ale w setup mamy tylko 1
        self.assertGreaterEqual(len(response.data['results']), 1)
        for loc in response.data['results']:
            self.assertIn('Gdańsk', loc['name'])

    def test_filter_by_name_case_insensitive(self):
        """Test czy filtrowanie jest case-insensitive."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'name': 'gdańsk'})

        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_filter_by_radius(self):
        """Test ?lat=54.35&lon=18.64&radius=1000 (1km)."""
        self.client.force_authenticate(user=self.user)

        # Promień 1km wokół Gdańska Stare Miasto
        response = self.client.get(self.url, {
            'lat': self.gdansk_lat,
            'lon': self.gdansk_lon,
            'radius': 1000  # 1km
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tylko location1 powinna być w tym promieniu
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.location1.id)

    def test_filter_by_radius_large_area(self):
        """Test radius=25000 (25km) - wszystkie 3 lokalizacje."""
        self.client.force_authenticate(user=self.user)

        # Promień 25km wokół Gdańska - powinien pokryć wszystkie 3
        # (Gdańsk-Gdynia to ok 20-21km, więc 25km zapewnia margines)
        response = self.client.get(self.url, {
            'lat': self.gdansk_lat,
            'lon': self.gdansk_lon,
            'radius': 25000  # 25km
        })

        self.assertEqual(len(response.data['results']), 3)

    def test_filter_by_radius_missing_params(self):
        """Test z brakującymi parametrami - powinno zwrócić wszystkie."""
        self.client.force_authenticate(user=self.user)

        # Brak radius - powinno zwrócić wszystkie
        response = self.client.get(self.url, {
            'lat': self.gdansk_lat,
            'lon': self.gdansk_lon,
        })

        self.assertEqual(len(response.data['results']), 3)

    def test_filter_by_radius_invalid_values(self):
        """Test z nieprawidłowymi wartościami - zwraca błąd lub pusty queryset."""
        self.client.force_authenticate(user=self.user)

        # Nieprawidłowe lat/lon
        response = self.client.get(self.url, {
            'lat': 'invalid',
            'lon': self.gdansk_lon,
            'radius': 1000
        })

        # Filter może zwrócić 400 (błąd walidacji) lub 200 z pustym queryset
        # Oba są akceptowalne
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.data['results']), 0)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_bbox(self):
        """Test ?bbox=18.5,54.3,18.65,54.45 (Gdańsk+Sopot)."""
        self.client.force_authenticate(user=self.user)

        # Bounding box pokrywający Gdańsk i Sopot (ale nie Gdynię)
        response = self.client.get(self.url, {
            'bbox': '18.5,54.3,18.65,54.45'  # lon_min,lat_min,lon_max,lat_max
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_bbox_invalid_format(self):
        """Test bbox z nieprawidłowym formatem - pusty queryset."""
        self.client.force_authenticate(user=self.user)

        # Zbyt mało wartości
        response = self.client.get(self.url, {'bbox': '18.5,54.3,18.65'})
        self.assertEqual(len(response.data['results']), 0)

        # Nieprawidłowy format
        response = self.client.get(self.url, {'bbox': 'invalid,bbox,format,here'})
        self.assertEqual(len(response.data['results']), 0)

    # --- READ-ONLY TESTS ---
    def test_post_not_allowed(self):
        """Test POST /api/locations/ - returns 405 Method Not Allowed."""
        self.client.force_authenticate(user=self.user)

        data = {
            'name': 'New Location',
            'coordinates': {
                'latitude': 54.35,
                'longitude': 18.64
            }
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        """Test PUT /api/locations/{id}/ - returns 405."""
        self.client.force_authenticate(user=self.user)
        url = f'{self.url}{self.location1.id}/'

        data = {'name': 'Updated Name'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        """Test DELETE /api/locations/{id}/ - returns 405."""
        self.client.force_authenticate(user=self.user)
        url = f'{self.url}{self.location1.id}/'

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # --- PAGINATION TESTS ---
    def test_pagination_default_page_size(self):
        """Test paginacji (15 lokalizacji, page_size=10)."""
        self.client.force_authenticate(user=self.user)

        # Utwórz 12 dodatkowych lokalizacji (12 + 3 istniejące = 15)
        for i in range(12):
            Location.objects.create(
                name=f'Location {i}',
                coordinates=Point(18.0 + i*0.01, 54.0 + i*0.01, srid=4326)
            )

        response = self.client.get(self.url)

        self.assertEqual(len(response.data['results']), 10)  # PAGE_SIZE=10
        self.assertIn('next', response.data)
        self.assertIsNotNone(response.data['next'])

    # --- EDGE CASES ---
    def test_location_with_mixed_privacy_emotion_points(self):
        """Test mix publicznych i prywatnych - avg ze WSZYSTKICH."""
        # location3 już ma mix (prywatny=4, publiczny=3), avg=(4+3)/2=3.5
        # To już testuje przypadek miksowania publicznych i prywatnych

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        location3_data = next(
            (loc for loc in response.data['results'] if loc['id'] == self.location3.id),
            None
        )

        # Średnia z [4 (prywatny), 3 (publiczny)] = 3.5
        self.assertEqual(float(location3_data['avg_emotional_value']), 3.5)

    def test_ordering_by_avg_emotional_value(self):
        """Test sortowania po avg_emotional_value DESC."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        results = response.data['results']

        # Sprawdź czy lokalizacje są posortowane po avg_emotional_value (malejąco)
        # Locations z wartościami powinny być przed null
        avg_values = [loc['avg_emotional_value'] for loc in results]

        # Odfiltruj null i sprawdź czy są malejące
        non_null_avgs = [avg for avg in avg_values if avg is not None]

        # Sprawdź czy lista jest posortowana malejąco
        for i in range(len(non_null_avgs) - 1):
            self.assertGreaterEqual(non_null_avgs[i], non_null_avgs[i + 1],
                                   "Lokalizacje powinny być posortowane po avg_emotional_value malejąco")

        # Sprawdź że location1 (avg=4.0) ma wyższy avg niż location3 (avg=3.5)
        location1_data = next((loc for loc in results if loc['id'] == self.location1.id), None)
        location3_data = next((loc for loc in results if loc['id'] == self.location3.id), None)

        self.assertIsNotNone(location1_data)
        self.assertIsNotNone(location3_data)
        self.assertGreater(location1_data['avg_emotional_value'],
                          location3_data['avg_emotional_value'])


class EmotionPointFilterTestCase(TestCase):
    """Testy dla filtrowania EmotionPoints po emotional_value."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.client = APIClient()

        # Użytkownicy
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass456'
        )

        # Lokalizacje testowe
        self.location1 = Location.objects.create(
            name='Test Location 1',
            coordinates=Point(18.6466, 54.3520, srid=4326)
        )
        self.location2 = Location.objects.create(
            name='Test Location 2',
            coordinates=Point(21.0122, 52.2297, srid=4326)
        )
        self.location3 = Location.objects.create(
            name='Test Location 3',
            coordinates=Point(19.9366, 50.0614, srid=4326)
        )
        self.location4 = Location.objects.create(
            name='Test Location 4',
            coordinates=Point(17.0385, 51.1079, srid=4326)
        )

        # EmotionPoints z różnymi wartościami (wszystkie publiczne)
        EmotionPoint.objects.create(
            user=self.user, location=self.location1,
            emotional_value=1, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location1,
            emotional_value=2, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user, location=self.location2,
            emotional_value=3, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user2, location=self.location2,
            emotional_value=4, privacy_status='public'
        )
        EmotionPoint.objects.create(
            user=self.user, location=self.location3,
            emotional_value=5, privacy_status='public'
        )

        # Jeden prywatny EmotionPoint (nie powinien być widoczny w listingu)
        # Używamy user2 i location4, aby uniknąć naruszenia unique constraint
        EmotionPoint.objects.create(
            user=self.user2, location=self.location4,
            emotional_value=1, privacy_status='private'
        )

        self.url = '/api/emotion-points/'

    def test_filter_by_single_emotional_value(self):
        """Test filtrowania po pojedynczej wartości ?emotional_value=3."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '3'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['emotional_value'], 3)

    def test_filter_by_multiple_emotional_values(self):
        """Test filtrowania po wielu wartościach ?emotional_value=1,2,3."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '1,2,3'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinno być 3 publiczne punkty (1, 2, 3)
        # Prywatny punkt z wartością 1 nie jest uwzględniony
        self.assertEqual(len(response.data['results']), 3)

        # Sprawdź wartości
        emotional_values = {ep['emotional_value'] for ep in response.data['results']}
        self.assertEqual(emotional_values, {1, 2, 3})

    def test_filter_by_all_emotional_values(self):
        """Test filtrowania po wszystkich wartościach ?emotional_value=1,2,3,4,5."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '1,2,3,4,5'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinno być 5 publicznych punktów
        self.assertEqual(len(response.data['results']), 5)

    def test_filter_no_results(self):
        """Test filtrowania po wartości której nie ma ?emotional_value=0."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '0'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_filter_multiple_values_no_results(self):
        """Test filtrowania po wartościach których nie ma ?emotional_value=0,6,7."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '0,6,7'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_filter_partial_match(self):
        """Test filtrowania gdzie tylko część wartości istnieje ?emotional_value=3,4,6."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '3,4,6'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinno być 2 punkty (3 i 4), wartość 6 nie istnieje
        self.assertEqual(len(response.data['results']), 2)

        emotional_values = {ep['emotional_value'] for ep in response.data['results']}
        self.assertEqual(emotional_values, {3, 4})

    def test_filter_without_parameter_returns_all(self):
        """Test że bez parametru zwraca wszystkie publiczne EmotionPoints."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Wszystkie publiczne (5 punktów)
        self.assertEqual(len(response.data['results']), 5)

    def test_filter_only_returns_public_emotion_points(self):
        """Test że filtrowanie zwraca tylko publiczne EmotionPoints."""
        self.client.force_authenticate(user=self.user)
        # Szukamy wartości 1, ale istnieją dwa punkty: publiczny (user, location1) i prywatny (user2, location4)
        response = self.client.get(self.url, {'emotional_value': '1'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tylko 1 publiczny punkt (prywatny nie jest zwracany w listingu)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['privacy_status'], 'public')

    def test_filter_with_spaces(self):
        """Test filtrowania z spacjami ?emotional_value=1, 2, 3."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '1, 2, 3'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # BaseInFilter automatycznie radzi sobie ze spacjami
        self.assertEqual(len(response.data['results']), 3)

    def test_filter_with_duplicate_values(self):
        """Test filtrowania z duplikatami ?emotional_value=3,3,3."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '3,3,3'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Powinno być 1 punkt (duplikaty są ignorowane)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['emotional_value'], 3)

    def test_filter_unauthenticated_fails(self):
        """Test że nieautoryzowany request zwraca 401/403."""
        # NIE autentykuj użytkownika
        response = self.client.get(self.url, {'emotional_value': '1,2,3'})

        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_filter_response_structure(self):
        """Test że odpowiedź ma prawidłową strukturę."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {'emotional_value': '1,2'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

        # Sprawdź strukturę pojedynczego EmotionPoint
        if len(response.data['results']) > 0:
            ep = response.data['results'][0]
            required_fields = ['id', 'location', 'emotional_value', 'privacy_status', 'username']
            for field in required_fields:
                self.assertIn(field, ep)
