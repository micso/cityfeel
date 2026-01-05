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
        """Przygotowanie srodowiska testowego."""
        self.client = APIClient()

        # Utworz uzytkownika testowego
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Wspolrzedne testowe (Warszawa, Plac Zamkowy)
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

        # Sprawdz status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz dane odpowiedzi
        self.assertEqual(response.data['emotional_value'], 4)
        self.assertEqual(response.data['privacy_status'], 'public')
        self.assertEqual(response.data['location']['coordinates']['latitude'], self.test_lat)
        self.assertEqual(response.data['location']['coordinates']['longitude'], self.test_lon)

        # Sprawdz czy utworzono w bazie
        self.assertEqual(EmotionPoint.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)

        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.user, self.user)
        self.assertEqual(emotion_point.emotional_value, 4)

    def test_update_existing_emotion_point(self):
        """Test aktualizacji istniejacego EmotionPoint."""
        self.client.force_authenticate(user=self.user)

        # Utworz poczatkowy punkt
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

        # Wyslij request z tymi samymi wspolrzednymi
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 5,
            'privacy_status': 'private'
        }

        response = self.client.post(self.url, data, format='json')

        # Sprawdz status code (POST zawsze zwraca 201)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz zaktualizowane wartosci
        self.assertEqual(response.data['emotional_value'], 5)
        self.assertEqual(response.data['privacy_status'], 'private')

        # Sprawdz ze nie utworzono duplikatu
        self.assertEqual(EmotionPoint.objects.count(), 1)
        self.assertEqual(Location.objects.count(), 1)

        # Sprawdz wartosci w bazie
        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.emotional_value, 5)
        self.assertEqual(emotion_point.privacy_status, 'private')

    def test_proximity_matching_uses_nearby_location(self):
        """Test czy proximity matching uzywa istniejacej Location w promieniu."""
        self.client.force_authenticate(user=self.user)

        # Utworz Location 30m od punktu testowego
        # Przesuniecie ~30m na polnoc (0.0003 stopnia ~ 30m)
        nearby_lat = self.test_lat + 0.0003
        nearby_point = Point(self.test_lon, nearby_lat, srid=4326)

        location = Location.objects.create(
            name='Nearby Location',
            coordinates=nearby_point
        )

        # Wyslij request z oryginalnym punktem
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz ze nie utworzono nowej Location
        self.assertEqual(Location.objects.count(), 1)

        # Sprawdz ze uzyto istniejacej Location
        emotion_point = EmotionPoint.objects.first()
        self.assertEqual(emotion_point.location, location)

    def test_proximity_matching_creates_new_location_if_far(self):
        """Test czy tworzy nowa Location jesli najblizsza jest poza promieniem."""
        self.client.force_authenticate(user=self.user)

        # Utworz Location 100m od punktu testowego (poza domyslnym promieniem 50m)
        # 0.001 stopnia ~ 100m
        far_lat = self.test_lat + 0.001
        far_point = Point(self.test_lon, far_lat, srid=4326)

        Location.objects.create(
            name='Far Location',
            coordinates=far_point
        )

        # Wyslij request z oryginalnym punktem
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz ze utworzono nowa Location
        self.assertEqual(Location.objects.count(), 2)

    def test_default_privacy_status_is_public(self):
        """Test czy domyslny privacy_status to 'public'."""
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
        # NIE autentykuj uzytkownika
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        # Moze byc 401 lub 403 w zaleznosci od konfiguracji DRF
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_invalid_emotional_value_too_low(self):
        """Test walidacji: emotional_value < 1."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 0,  # Nieprawidlowe
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('emotional_value', response.data)

    def test_invalid_emotional_value_too_high(self):
        """Test walidacji: emotional_value > 5."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 6,  # Nieprawidlowe
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('emotional_value', response.data)

    def test_invalid_latitude_too_low(self):
        """Test walidacji: latitude < -90."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(-91.0, self.test_lon),  # Nieprawidlowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_latitude_too_high(self):
        """Test walidacji: latitude > 90."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(91.0, self.test_lon),  # Nieprawidlowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_longitude_too_low(self):
        """Test walidacji: longitude < -180."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, -181.0),  # Nieprawidlowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_longitude_too_high(self):
        """Test walidacji: longitude > 180."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, 181.0),  # Nieprawidlowe
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)

    def test_invalid_privacy_status(self):
        """Test walidacji: nieprawidlowy privacy_status."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
            'privacy_status': 'invalid_status',  # Nieprawidlowe
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
        """Test wartosci granicznych latitude (-90, 90)."""
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
            'location': self.make_location_data(90.0, 0.0),  # Zmieniona longitude zeby byl nowy punkt
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_edge_case_longitude_boundary_values(self):
        """Test wartosci granicznych longitude (-180, 180)."""
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
            'location': self.make_location_data(10.0, 180.0),  # Zmieniona latitude zeby byl nowy punkt
            'emotional_value': 4,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_multiple_users_same_location(self):
        """Test: rozni uzytkownicy moga dodac EmotionPoint na tej samej Location."""
        self.client.force_authenticate(user=self.user)

        # Pierwszy uzytkownik dodaje punkt
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
        }
        response1 = self.client.post(self.url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Drugi uzytkownik
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=user2)

        # Drugi uzytkownik dodaje punkt na tej samej Location
        response2 = self.client.post(self.url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Sprawdz ze sa 2 EmotionPointy
        self.assertEqual(EmotionPoint.objects.count(), 2)
        # Ale tylko 1 Location
        self.assertEqual(Location.objects.count(), 1)

    def test_response_contains_all_required_fields(self):
        """Test czy odpowiedz zawiera wszystkie wymagane pola."""
        self.client.force_authenticate(user=self.user)

        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon),
            'emotional_value': 4,
            'privacy_status': 'public',
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz obecnosc wszystkich pol top-level
        required_fields = [
            'id',
            'location',
            'emotional_value',
            'privacy_status',
            'username',
        ]

        for field in required_fields:
            self.assertIn(field, response.data, f"Brak pola '{field}' w odpowiedzi")

        # Sprawdz obecnosc pol w nested location
        location_fields = ['id', 'name', 'coordinates']
        for field in location_fields:
            self.assertIn(field, response.data['location'], f"Brak pola '{field}' w location")

        # Sprawdz obecnosc pol w nested coordinates
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

        # Sprawdz format nazwy lokalizacji
        expected_name = "Lat: 52.2297, Lon: 21.0122"
        self.assertEqual(response.data['location']['name'], expected_name)

        # Sprawdz ze Location w bazie ma te sama nazwe
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, expected_name)

    def test_custom_location_name(self):
        """Test czy mozna podac wlasna nazwe lokalizacji."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Plac Zamkowy"
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, custom_name),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz czy uzyto podanej nazwy
        self.assertEqual(response.data['location']['name'], custom_name)

        # Sprawdz ze Location w bazie ma te nazwe
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, custom_name)

    def test_custom_location_name_overrides_auto_generation(self):
        """Test czy wlasna nazwa ma pierwszenstwo przed auto-generowana."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Moja ulubiona kawiarnia"
        data = {
            'location': self.make_location_data(50.0614, 19.9366, custom_name),
            'emotional_value': 5,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Sprawdz ze nie zostala uzyta auto-generowana nazwa
        self.assertNotEqual(response.data['location']['name'], "Lat: 50.0614, Lon: 19.9366")
        # Sprawdz ze uzyto nazwy podanej przez uzytkownika
        self.assertEqual(response.data['location']['name'], custom_name)

    def test_location_name_max_length_validation(self):
        """Test walidacji: location_name dluzsza niz 200 znakow."""
        self.client.force_authenticate(user=self.user)

        # Nazwa 201 znakow (za dluga)
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
        """Test czy nazwa lokalizacji moze zawierac znaki specjalne i polskie znaki."""
        self.client.force_authenticate(user=self.user)

        custom_name = "Kawiarnia \"Pod Aniolem\" - ul. Swietokrzyska 10/12"
        data = {
            'location': self.make_location_data(self.test_lat, self.test_lon, custom_name),
            'emotional_value': 4,
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['location']['name'], custom_name)

        # Sprawdz w bazie
        location = Location.objects.get(id=response.data['location']['id'])
        self.assertEqual(location.name, custom_name)


class LocationAPITestCase(TestCase):
    """
    Testy dla endpointu GET /api/locations/ (Zadanie #35).
    Sprawdza obliczanie sredniej (avg_emotional_value) i liczby opinii.
    """

    def setUp(self):
        self.client = APIClient()
        # Tworzymy dwoch uzytkownikow, aby moc dodac >1 opinie do jednej lokalizacji
        self.user = User.objects.create_user(username='testuser_loc', password='password')
        self.user2 = User.objects.create_user(username='testuser_loc2', password='password')
        
        self.client.force_authenticate(user=self.user)
        self.url = '/api/locations/'

        # Lokalizacja 1: Same publiczne opinie (5 i 3) -> Srednia powinna byc 4.0
        self.loc1 = Location.objects.create(name='Loc1', coordinates=Point(1, 1, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc1, emotional_value=5, privacy_status='public')
        EmotionPoint.objects.create(user=self.user2, location=self.loc1, emotional_value=3, privacy_status='public')

        # Lokalizacja 2: Brak opinii
        self.loc2 = Location.objects.create(name='Loc2', coordinates=Point(2, 2, srid=4326))

        # Lokalizacja 3: Mieszane (4 publiczna, 1 prywatna) -> Srednia 4.0 (prywatna ignorowana)
        self.loc3 = Location.objects.create(name='Loc3', coordinates=Point(3, 3, srid=4326))
        EmotionPoint.objects.create(user=self.user, location=self.loc3, emotional_value=4, privacy_status='public')
        EmotionPoint.objects.create(user=self.user2, location=self.loc3, emotional_value=1, privacy_status='private')

    def test_response_fields(self):
        """Sprawdza obecnosc pol (stare nazwy z mastera)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data['results']) > 0:
            data = response.data['results'][0]
            self.assertIn('avg_emotional_value', data)
            self.assertIn('emotion_points_count', data)

    def test_average_rating_calculation(self):
        """Sprawdza poprawnosc obliczania sredniej dla Loc1 (tylko publiczne)."""
        response = self.client.get(f'{self.url}{self.loc1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # (5 + 3) / 2 = 4.0
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 2)

    def test_private_opinions_ignored(self):
        """Sprawdza dla Loc3 czy opinia prywatna jest ignorowana w sredniej."""
        response = self.client.get(f'{self.url}{self.loc3.id}/')
        
        # Oczekujemy 4.0 (tylko ocena publiczna), a nie sredniej z obu
        self.assertEqual(response.data['avg_emotional_value'], 4.0)
        self.assertEqual(response.data['emotion_points_count'], 1)

    def test_no_opinions_values(self):
        """Sprawdza wartosci dla lokalizacji bez opinii."""
        response = self.client.get(f'{self.url}{self.loc2.id}/')
        
        self.assertIsNone(response.data['avg_emotional_value'])
        self.assertEqual(response.data['emotion_points_count'], 0)