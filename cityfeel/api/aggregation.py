"""
Helpers agregacji emocji dla LocationViewSet.

Model EmotionPoint jest historyczny — wiele wpisów per (user, location). Zbiorcze
średnie miejsca liczymy w dwóch trybach:

A. **Stan bieżący** (bez filtra czasu) — średnia z najnowszych głosów każdego usera
   (DISTINCT ON (user_id) ORDER BY created_at DESC). Indeks
   ``emotions_loc_user_created_idx`` na ``(location, user, -created_at)`` powoduje, że
   PostgreSQL wykonuje to przez Index Scan, bez sortu w pamięci.

B. **W oknie czasu** (z filtrem ``created_after`` / ``created_before``) — mean-of-means:
   dla każdego usera w oknie liczymy jego średnią, potem uśredniamy po userach.
   Każdy user ma jedną wagę niezależnie od liczby wpisów w oknie.

Obie agregacje wstrzykiwane są jako annotacja ``avg_emotional_value`` na queryset
``Location`` przez ``RawSQL`` — czytelne, sprawdzalne i wykorzystujące indeksy.
"""
from django.db.models import Count
from django.db.models.expressions import RawSQL


_LATEST_PER_USER_AVG_SQL = """
    SELECT AVG(sub.emotional_value)
    FROM (
        SELECT DISTINCT ON (e.user_id) e.user_id, e.emotional_value
        FROM emotions_emotion_point e
        WHERE e.location_id = "map_location"."id"
        ORDER BY e.user_id, e.created_at DESC
    ) sub
"""


_WINDOWED_MEAN_OF_MEANS_SQL = """
    SELECT AVG(per_user.user_avg)
    FROM (
        SELECT e.user_id, AVG(e.emotional_value) AS user_avg
        FROM emotions_emotion_point e
        WHERE e.location_id = "map_location"."id"
          AND e.created_at >= %s
          AND e.created_at <= %s
        GROUP BY e.user_id
    ) per_user
"""


_WINDOWED_COUNT_SQL = """
    SELECT COUNT(*)
    FROM emotions_emotion_point e
    WHERE e.location_id = "map_location"."id"
      AND e.created_at >= %s
      AND e.created_at <= %s
"""


def annotate_latest_per_user_avg(qs):
    """
    Annotuje ``Location`` queryset polami ``avg_emotional_value`` (tryb A — latest per user)
    oraz ``emotion_points_count`` (zliczenie wszystkich wpisów historii).
    """
    return qs.annotate(
        avg_emotional_value=RawSQL(_LATEST_PER_USER_AVG_SQL, []),
        emotion_points_count=Count('emotion_points'),
    )


def annotate_windowed_mean_of_means_avg(qs, created_after, created_before):
    """
    Annotuje ``Location`` queryset polami:
    - ``avg_emotional_value`` (tryb B — mean-of-means w oknie ``[created_after, created_before]``)
    - ``emotion_points_count`` (liczba wpisów emocji wewnątrz okna)

    Oba parametry to obiekty ``datetime`` (wymagane razem; brak okna = używaj trybu A).
    """
    params = [created_after, created_before]
    return qs.annotate(
        avg_emotional_value=RawSQL(_WINDOWED_MEAN_OF_MEANS_SQL, params),
        emotion_points_count=RawSQL(_WINDOWED_COUNT_SQL, params),
    )
