#!/usr/bin/env python3
"""
Skrypt generujący Django fixtures dla projektu CityFeel.

Generuje:
- 50 lokalizacji w Trójmieście
- ~78 EmotionPoints (0-4 per lokalizacja)
- ~43 komentarze (do Location + EmotionPoint)

Użycie:
    python cityfeel/fixtures/generate_fixtures.py
    # lub:
    uv run cityfeel/fixtures/generate_fixtures.py
"""

import json
import random
import os
import sys
from datetime import datetime, timedelta

# Dodaj cityfeel/fixtures do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from locations_data import LOCATIONS, CLUSTER_EMOTIONS
from comment_templates import COMMENT_TEMPLATES_BY_VALUE, COMMENTS_REPLY

# Konfiguracja
USERS = [1, 8, 9, 10]  # admin, starluna, byteforge, emberleaf
PRIVACY_WEIGHTS = [0.7, 0.3]  # 70% public, 30% private
OUTPUT_FILE = "cityfeel/fixtures/cityfeel_data.json"

# Seed dla powtarzalności (opcjonalnie)
random.seed(42)


def generate_location(pk, data):
    """
    Generuje Location fixture z formatem EWKT dla PostGIS.

    Args:
        pk: Primary key
        data: Słownik z name, lon, lat

    Returns:
        Dict z fixture Location
    """
    return {
        "model": "map.location",
        "pk": pk,
        "fields": {
            "name": data["name"],
            # Format EWKT: SRID=4326;POINT(longitude latitude) - WAŻNE: przestrzeń, nie przecinek!
            "coordinates": f"SRID=4326;POINT({data['lon']} {data['lat']})"
        }
    }


def generate_emotion_points(locations):
    """
    Generuje EmotionPoints z walidacją unique_together(user, location).

    Rozkład:
    - 10 lokalizacji × 0 emocji = 0
    - 15 lokalizacji × 1 emocja = 15
    - 15 lokalizacji × 2 emocje = 30
    - 7 lokalizacji × 3 emocje = 21
    - 3 lokalizacje × 4 emocje = 12
    Total: 78 EmotionPoints

    Args:
        locations: Lista słowników z danymi lokalizacji

    Returns:
        Lista fixtures EmotionPoint
    """
    emotion_points = []
    pk = 1

    # Rozkład ilości emocji per lokalizacja
    emotion_counts = [0] * 10 + [1] * 15 + [2] * 15 + [3] * 7 + [4] * 3
    random.shuffle(emotion_counts)

    for loc_idx, count in enumerate(emotion_counts):
        location = locations[loc_idx]
        location_pk = loc_idx + 1

        # Wybierz unikalnych użytkowników dla tej lokalizacji
        # (zapewnia constraint unique_together(user, location))
        users_for_location = random.sample(USERS, count)

        for user_id in users_for_location:
            # Emotional value bazując na cluster
            cluster = location.get("cluster", "neutral")
            emotional_values = CLUSTER_EMOTIONS.get(cluster, [2, 3, 4])
            emotional_value = random.choice(emotional_values)

            # Privacy status (70% public, 30% private)
            privacy_status = random.choices(["public", "private"], weights=PRIVACY_WEIGHTS)[0]

            # Timestamp - losowy w ostatnich 60 dniach
            days_ago = random.randint(1, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_at = (
                datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            ).isoformat()

            emotion_points.append({
                "model": "emotions.emotionpoint",
                "pk": pk,
                "fields": {
                    "user": user_id,
                    "location": location_pk,
                    "emotional_value": emotional_value,
                    "privacy_status": privacy_status,
                    "created_at": created_at,
                    "updated_at": created_at
                }
            })
            pk += 1

    return emotion_points


def generate_comments(locations, emotion_points):
    """
    Generuje Comments (do Location i do EmotionPoint).

    - 40% lokalizacji (20 lokalizacji): 0-3 komentarze per lokalizacja
    - 15% lokalizacji (~8): komentarz per EmotionPoint

    Args:
        locations: Lista słowników z danymi lokalizacji
        emotion_points: Lista fixtures EmotionPoint

    Returns:
        Lista fixtures Comment
    """
    comments = []
    pk = 1

    # === KOMENTARZE DO LOKALIZACJI (40% = 20 lokalizacji) ===
    locations_with_comments = random.sample(range(50), 20)

    # Rozkład: 10×1, 7×2, 3×3 komentarze
    comment_counts = [1] * 10 + [2] * 7 + [3] * 3

    for loc_idx, count in zip(locations_with_comments, comment_counts):
        location_pk = loc_idx + 1
        location = locations[loc_idx]

        for _ in range(count):
            user_id = random.choice(USERS)

            # Treść komentarza bazując na cluster lokalizacji
            cluster = location.get("cluster", "neutral")
            if "positive" in cluster:
                # Pozytywne komentarze (4-5)
                emotional_value = random.choice([4, 5])
            elif "negative" in cluster:
                # Negatywne komentarze (1-2)
                emotional_value = random.choice([1, 2])
            else:
                # Neutralne/mieszane (2-4)
                emotional_value = random.choice([2, 3, 4])

            content = random.choice(COMMENT_TEMPLATES_BY_VALUE[emotional_value])

            privacy_status = random.choice(["public", "private"])

            # Timestamp - losowy w ostatnich 60 dniach
            days_ago = random.randint(1, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_at = (
                datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            ).isoformat()

            comments.append({
                "model": "emotions.comment",
                "pk": pk,
                "fields": {
                    "user": user_id,
                    "location": location_pk,  # REQUIRED!
                    "emotion_point": None,  # Komentarz do Location
                    "content": content,
                    "privacy_status": privacy_status,
                    "created_at": created_at
                }
            })
            pk += 1

    # === KOMENTARZE DO EMOTIONPOINT (15% lokalizacji ~= 8 EmotionPoints) ===
    if len(emotion_points) > 0:
        num_ep_comments = min(10, len(emotion_points))
        emotion_points_with_comments = random.sample(emotion_points, num_ep_comments)

        for ep in emotion_points_with_comments:
            user_id = random.choice(USERS)
            ep_pk = ep["pk"]
            location_pk = ep["fields"]["location"]

            # Komentarz odpowiedzi
            content = random.choice(COMMENTS_REPLY)

            privacy_status = random.choice(["public", "private"])

            # Timestamp - później niż EmotionPoint
            ep_created = datetime.fromisoformat(ep["fields"]["created_at"])
            days_after = random.randint(1, 10)
            hours_after = random.randint(0, 23)
            created_at = (ep_created + timedelta(days=days_after, hours=hours_after)).isoformat()

            comments.append({
                "model": "emotions.comment",
                "pk": pk,
                "fields": {
                    "user": user_id,
                    "location": location_pk,  # REQUIRED!
                    "emotion_point": ep_pk,  # FK do EmotionPoint
                    "content": content,
                    "privacy_status": privacy_status,
                    "created_at": created_at
                }
            })
            pk += 1

    return comments


def validate_unique_together(emotion_points):
    """
    Waliduje constraint unique_together(user, location).

    Args:
        emotion_points: Lista fixtures EmotionPoint

    Raises:
        ValueError: Jeśli constraint jest naruszony
    """
    seen = set()
    for ep in emotion_points:
        user_id = ep["fields"]["user"]
        location_id = ep["fields"]["location"]
        key = (user_id, location_id)

        if key in seen:
            raise ValueError(f"Duplicate (user, location): {key}")
        seen.add(key)

    print("✓ Constraint unique_together validated")


def validate_foreign_keys(emotion_points, comments, location_count):
    """
    Waliduje poprawność foreign keys.

    Args:
        emotion_points: Lista fixtures EmotionPoint
        comments: Lista fixtures Comment
        location_count: Ilość lokalizacji

    Raises:
        AssertionError: Jeśli FK są niepoprawne
    """
    valid_users = [1, 8, 9, 10]
    valid_locations = list(range(1, location_count + 1))
    valid_emotion_points = [ep["pk"] for ep in emotion_points]

    # Walidacja EmotionPoints
    for ep in emotion_points:
        assert ep["fields"]["user"] in valid_users, f"Invalid user FK: {ep['fields']['user']}"
        assert ep["fields"]["location"] in valid_locations, f"Invalid location FK: {ep['fields']['location']}"

    # Walidacja Comments
    for comment in comments:
        assert comment["fields"]["user"] in valid_users, f"Invalid user FK: {comment['fields']['user']}"
        assert comment["fields"]["location"] in valid_locations, f"Invalid location FK: {comment['fields']['location']}"

        ep_id = comment["fields"]["emotion_point"]
        if ep_id is not None:
            assert ep_id in valid_emotion_points, f"Invalid emotion_point FK: {ep_id}"

    print("✓ Foreign keys validated")


def main():
    """
    Główna funkcja generująca fixtures.
    """
    print("=" * 60)
    print("CityFeel Fixtures Generator")
    print("=" * 60)

    fixtures = []

    # 1. Generuj Locations
    print("\n[1/5] Generating locations...")
    location_fixtures = [generate_location(idx + 1, loc) for idx, loc in enumerate(LOCATIONS)]
    fixtures.extend(location_fixtures)
    print(f"  ✓ Generated {len(location_fixtures)} locations")

    # 2. Generuj EmotionPoints
    print("\n[2/5] Generating emotion points...")
    emotion_fixtures = generate_emotion_points(LOCATIONS)
    fixtures.extend(emotion_fixtures)
    print(f"  ✓ Generated {len(emotion_fixtures)} emotion points")

    # 3. Generuj Comments
    print("\n[3/5] Generating comments...")
    comment_fixtures = generate_comments(LOCATIONS, emotion_fixtures)
    fixtures.extend(comment_fixtures)
    print(f"  ✓ Generated {len(comment_fixtures)} comments")

    # 4. Walidacja
    print("\n[4/5] Validating data...")
    validate_unique_together(emotion_fixtures)
    validate_foreign_keys(emotion_fixtures, comment_fixtures, len(location_fixtures))

    # 5. Zapisz do JSON
    print("\n[5/5] Writing to JSON...")
    output_path = OUTPUT_FILE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved to: {output_path}")

    # Podsumowanie
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total objects:    {len(fixtures)}")
    print(f"  - Locations:    {len(location_fixtures)}")
    print(f"  - EmotionPoints: {len(emotion_fixtures)}")
    print(f"  - Comments:     {len(comment_fixtures)}")
    print("\nNext steps:")
    print(f"  1. Validate JSON: uv run python -m json.tool {output_path} > /dev/null && echo 'JSON valid'")
    print(f"  2. Load to DB: uv run cityfeel/manage.py loaddata {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
