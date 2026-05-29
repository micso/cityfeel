"""
Testy filtra czasowego emocji: model historyczny, dwa tryby agregacji
(latest-per-user vs mean-of-means), endpointy histogramu i timeline lokalizacji.
"""
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from emotions.models import EmotionPoint
from map.models import Location

User = get_user_model()


def _set_created_at(emotion_point, dt):
    """
    auto_now_add ustawia created_at podczas create — żeby testować różne momenty,
    nadpisujemy bezpośrednio przez QuerySet.update (które nie woła auto_now_add).
    """
    EmotionPoint.objects.filter(pk=emotion_point.pk).update(created_at=dt)
    emotion_point.refresh_from_db()


class HistoricalModelTestCase(TestCase):
    """Model historyczny: wiele wpisów per (user, location) jest dozwolone."""

    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='x')
        self.location = Location.objects.create(
            name='L', coordinates=Point(18.6, 54.35, srid=4326)
        )

    def test_user_can_have_multiple_entries_for_same_location(self):
        EmotionPoint.objects.create(
            user=self.user, location=self.location,
            emotional_value=2, privacy_status='public',
        )
        EmotionPoint.objects.create(
            user=self.user, location=self.location,
            emotional_value=4, privacy_status='public',
        )
        self.assertEqual(
            EmotionPoint.objects.filter(user=self.user, location=self.location).count(),
            2
        )


class LocationAvgAggregationTestCase(TestCase):
    """
    Agregacja avg_emotional_value w LocationViewSet:
    - tryb A (latest-per-user) bez params czasu,
    - tryb B (mean-of-means) z params czasu.
    """

    url = '/api/locations/'

    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username='alice', password='x')
        self.bob = User.objects.create_user(username='bob', password='x')
        self.viewer = User.objects.create_user(username='viewer', password='x')

        self.location = Location.objects.create(
            name='Plac', coordinates=Point(18.6, 54.35, srid=4326)
        )

        self.t_jan = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        self.t_feb = datetime(2026, 2, 15, 12, 0, tzinfo=timezone.utc)
        self.t_mar = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)

        # Alice: w styczniu 1, w marcu 5 (latest = 5).
        a1 = EmotionPoint.objects.create(
            user=self.alice, location=self.location,
            emotional_value=1, privacy_status='public',
        )
        _set_created_at(a1, self.t_jan)
        a2 = EmotionPoint.objects.create(
            user=self.alice, location=self.location,
            emotional_value=5, privacy_status='public',
        )
        _set_created_at(a2, self.t_mar)

        # Bob: tylko w lutym 3.
        b1 = EmotionPoint.objects.create(
            user=self.bob, location=self.location,
            emotional_value=3, privacy_status='public',
        )
        _set_created_at(b1, self.t_feb)

        self.client.force_authenticate(user=self.viewer)

    def _get_avg(self, query=''):
        response = self.client.get(self.url + query)
        self.assertEqual(response.status_code, 200)
        results = response.data
        # Lista lub dict z paginacją — LocationViewSet ma pagination_class=None, więc lista.
        loc = next(r for r in results if r['id'] == self.location.id)
        return loc['avg_emotional_value']

    def test_mode_a_uses_latest_per_user(self):
        """Bez filtra czasu: latest per user → (5 + 3) / 2 = 4.0."""
        avg = self._get_avg()
        self.assertAlmostEqual(float(avg), 4.0, places=2)

    def test_mode_b_window_february_only(self):
        """Okno luty: tylko Bob (3) → 3.0."""
        q = (
            '?created_after=2026-02-01T00:00:00Z'
            '&created_before=2026-02-28T23:59:59Z'
        )
        avg = self._get_avg(q)
        self.assertAlmostEqual(float(avg), 3.0, places=2)

    def test_mode_b_window_january(self):
        """Okno styczeń: tylko Alice (1) → 1.0 (a NIE 5, bo w styczniu jeszcze nie kliknęła 5)."""
        q = (
            '?created_after=2026-01-01T00:00:00Z'
            '&created_before=2026-01-31T23:59:59Z'
        )
        avg = self._get_avg(q)
        self.assertAlmostEqual(float(avg), 1.0, places=2)

    def test_mode_b_full_window_uses_mean_of_means(self):
        """
        Okno styczeń–marzec: Alice ma dwa wpisy (1 i 5) → jej user_avg = 3;
        Bob ma jeden (3) → user_avg = 3. Mean-of-means = (3 + 3) / 2 = 3.0.
        Tymczasem prosta średnia (1+5+3)/3 = 3.0 też daje 3.0 — to akurat zbieg.
        Zmieniamy danymi, by rozróżnić oba tryby.
        """
        # Dodaj Alice trzeci wpis w lutym o wartości 1, żeby skrzywić prostą średnią.
        extra = EmotionPoint.objects.create(
            user=self.alice, location=self.location,
            emotional_value=1, privacy_status='public',
        )
        _set_created_at(extra, self.t_feb)

        q = (
            '?created_after=2026-01-01T00:00:00Z'
            '&created_before=2026-03-31T23:59:59Z'
        )
        avg = self._get_avg(q)
        # Alice user_avg = (1+5+1)/3 = 2.333...; Bob = 3. Mean-of-means = (2.333 + 3)/2 = 2.6667
        self.assertAlmostEqual(float(avg), (7 / 3 + 3) / 2, places=2)

    def test_mode_b_excludes_entries_outside_window(self):
        """Okno daleko poza danymi → punkt zostaje całkowicie odfiltrowany i znika z mapy."""
        q = (
            '?created_after=2030-01-01T00:00:00Z'
            '&created_before=2030-01-31T23:59:59Z'
        )

        # --- NOWA LOGIKA (Aktualna) ---
        # Oczekujemy, że funkcja _get_avg rzuci StopIteration, bo lokalizacja
        # wyparowała z wyników API z powodu braku aktywności w tym oknie czasowym.
        with self.assertRaises(StopIteration):
            self._get_avg(q)

        """
        # --- STARA LOGIKA (Kopia Zapasowa) ---
        # Jeśli kierownik zdecyduje, że martwe punkty mają jednak wisieć na mapie (ze średnią None),
        # musisz usunąć powyższy blok "with self.assertRaises..." i odkomentować te dwie linijki:
        #
        # avg = self._get_avg(q)
        # self.assertIsNone(avg)
        # 
        # UWAGA: Aby stara logika testu znów działała na zielono, musisz też usunąć 
        # ".filter(time_filter)" przy definicji "fast_ids" w pliku api/views.py!
        """


class HistogramEndpointTestCase(TestCase):
    url = '/api/emotion-points/histogram/'

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='u', password='x')
        self.location = Location.objects.create(
            name='L', coordinates=Point(18.6, 54.35, srid=4326)
        )

        # 3 wpisy: dwa 1 stycznia, jeden 2 stycznia.
        e1 = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=2, privacy_status='public',
        )
        _set_created_at(e1, datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc))
        e2 = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=4, privacy_status='public',
        )
        _set_created_at(e2, datetime(2026, 1, 1, 18, 0, tzinfo=timezone.utc))
        e3 = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=5, privacy_status='public',
        )
        _set_created_at(e3, datetime(2026, 1, 2, 12, 0, tzinfo=timezone.utc))

        self.client.force_authenticate(user=self.user)

    def test_histogram_day_buckets(self):
        response = self.client.get(self.url + '?bucket=day')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        day1, day2 = response.data
        self.assertEqual(day1['count'], 2)
        self.assertAlmostEqual(day1['avg_value'], 3.0, places=2)
        self.assertEqual(day2['count'], 1)
        self.assertAlmostEqual(day2['avg_value'], 5.0, places=2)

    def test_histogram_invalid_bucket(self):
        response = self.client.get(self.url + '?bucket=year')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_histogram_respects_time_filter(self):
        response = self.client.get(
            self.url + '?bucket=day&created_after=2026-01-02T00:00:00Z'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['count'], 1)


class LocationTimelineEndpointTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='u', password='x')
        self.location = Location.objects.create(
            name='L', coordinates=Point(18.6, 54.35, srid=4326)
        )
        self.other_location = Location.objects.create(
            name='Other', coordinates=Point(20.0, 50.0, srid=4326)
        )

        e1 = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=3, privacy_status='public',
        )
        _set_created_at(e1, datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc))
        e2 = EmotionPoint.objects.create(
            user=self.user, location=self.location, emotional_value=5, privacy_status='public',
        )
        _set_created_at(e2, datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc))

        # Wpis dla innej lokalizacji — nie powinien wystąpić w timeline.
        e3 = EmotionPoint.objects.create(
            user=self.user, location=self.other_location, emotional_value=1, privacy_status='public',
        )
        _set_created_at(e3, datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc))

        self.client.force_authenticate(user=self.user)

    def test_timeline_returns_only_for_given_location(self):
        url = f'/api/locations/{self.location.id}/emotion-timeline/?bucket=day'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertAlmostEqual(response.data[0]['avg_value'], 3.0, places=2)
        self.assertAlmostEqual(response.data[1]['avg_value'], 5.0, places=2)