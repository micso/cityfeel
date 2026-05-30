import os
import sys
import django
import random
import time
from datetime import timedelta

# --- INICJALIZACJA ŚRODOWISKA DJANGO ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cityfeel.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.db import connection
from map.models import Location
from emotions.models import EmotionPoint

User = get_user_model()
BATCH_SIZE = 10000  # Optymalna paczka dla PostgreSQL


def fix_database_sync():
    try:
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE emotions_emotion_point ALTER COLUMN is_hidden DROP NOT NULL;')
    except Exception:
        pass


def get_random_land_coordinates_in_gdansk():
    zones = [
        {'lat_min': 54.33, 'lat_max': 54.42, 'lon_min': 18.55, 'lon_max': 18.65},
        {'lat_min': 54.32, 'lat_max': 54.42, 'lon_min': 18.46, 'lon_max': 18.55},
        {'lat_min': 54.27, 'lat_max': 54.33, 'lon_min': 18.55, 'lon_max': 18.65},
        {'lat_min': 54.35, 'lat_max': 54.38, 'lon_min': 18.65, 'lon_max': 18.72},
        {'lat_min': 54.32, 'lat_max': 54.35, 'lon_min': 18.72, 'lon_max': 18.85},
    ]
    zone = random.choice(zones)
    lat = random.uniform(zone['lat_min'], zone['lat_max'])
    lon = random.uniform(zone['lon_min'], zone['lon_max'])
    return lat, lon


def main():
    print("\n" + "🔥" * 25)
    print("🚀  GENERATOR MASOWY BIG DATA (CITYFEEL)  🚀")
    print("🔥" * 25)
    print("\nUWAGA: Ten skrypt nadpisuje ograniczenia sprzętowe poprzez techniki Bulk Insert.")

    fix_database_sync()

    try:
        users_count = int(input("1. Ile UŻYTKOWNIKÓW wygenerować? (np. 100000): ") or 0)
        locs_count = int(input("2. Ile LOKALIZACJI wygenerować? (np. 1000000): ") or 0)
        emotions_count = int(input("3. Ile OPINII wygenerować? (np. 10000000): ") or 0)
    except ValueError:
        print("BŁĄD: Wprowadzono niepoprawną wartość.")
        return

    start_time = time.time()

    # ==========================================
    # 1. TWORZENIE UŻYTKOWNIKÓW (Szybkie haszowanie)
    # ==========================================
    if users_count > 0:
        print(f"\n[1/3] Generowanie {users_count} użytkowników...")
        # Haszujemy hasło tylko RAZ
        hashed_password = make_password('HasloTestowe123!')

        users_batch = []
        total_created_users = 0
        base_username_id = random.randint(100000, 999999)

        for i in range(users_count):
            username = f"mass_user_{base_username_id}_{i}"
            users_batch.append(User(username=username, password=hashed_password))

            if len(users_batch) >= BATCH_SIZE:
                User.objects.bulk_create(users_batch)
                total_created_users += len(users_batch)
                users_batch = []
                print(f"  -> Zapisano {total_created_users} / {users_count} użytkowników...")

        if users_batch:  # Resztki
            User.objects.bulk_create(users_batch)
            total_created_users += len(users_batch)
            print(f"  -> Zapisano {total_created_users} / {users_count} użytkowników...")

        # Zapiszmy informację o koncie głównym do testów (pierwsze wygenerowane)
        if total_created_users > 0:
            print(f"💡 Przykładowe konto: Login: mass_user_{base_username_id}_0 | Hasło: HasloTestowe123!")

    # ==========================================
    # 2. TWORZENIE LOKALIZACJI
    # ==========================================
    if locs_count > 0:
        print(f"\n[2/3] Generowanie {locs_count} lokalizacji na lądzie...")
        categories = ['Szkoła', 'Park', 'Siłownia', 'Plaża', 'Kawiarnia', 'Restauracja', 'Przystanek', 'Sklep']
        districts = ['w Śródmieściu', 'we Wrzeszczu', 'w Oliwie', 'na Przymorzu', 'w Brzeźnie', 'w Osowej',
                     'na Chełmie']

        locs_batch = []
        total_created_locs = 0

        for i in range(locs_count):
            cat = random.choice(categories)
            dist = random.choice(districts)
            lat, lon = get_random_land_coordinates_in_gdansk()

            # Aby uniknąć ciągłego szukania unikalnej nazwy, przypisujemy jej unikalny znacznik ID
            name = f"{cat} {dist} [UID-{random.randint(1000, 9999)}-{i}]"

            locs_batch.append(Location(name=name, coordinates=Point(lon, lat, srid=4326)))

            if len(locs_batch) >= BATCH_SIZE:
                Location.objects.bulk_create(locs_batch)
                total_created_locs += len(locs_batch)
                locs_batch = []
                print(f"  -> Zapisano {total_created_locs} / {locs_count} lokalizacji...")

        if locs_batch:
            Location.objects.bulk_create(locs_batch)
            total_created_locs += len(locs_batch)
            print(f"  -> Zapisano {total_created_locs} / {locs_count} lokalizacji...")

    # ==========================================
    # 3. TWORZENIE EMOCJI (Z ominięciem auto_now_add)
    # ==========================================
    if emotions_count > 0:
        print(f"\n[3/3] Przygotowywanie danych do wylosowania {emotions_count} opinii...")

        # Pobieramy Z BAZY wyłącznie surowe ID, zamiast ładować całe obiekty (Oszczędza Gigabajty RAM)
        user_ids = list(User.objects.values_list('id', flat=True))
        loc_ids = list(Location.objects.values_list('id', flat=True))

        if not user_ids or not loc_ids:
            print("❌ BŁĄD: Baza musi zawierać użytkowników i lokalizacje!")
            return

        # Pamięć podręczna na wylosowane pary (aby uniknąć duplikatów 1 osoba = 1 lokalizacja)
        existing_pairs = set()

        # HACK: Wyłączamy wymuszanie dzisiejszej daty na czas działania generatora
        created_at_field = EmotionPoint._meta.get_field('created_at')
        created_at_field.auto_now_add = False

        emotions_batch = []
        total_created_emotions = 0
        now = timezone.now()

        print(f"  Generowanie opinii. To może chwilę potrwać...")
        for i in range(emotions_count):
            u_id = random.choice(user_ids)
            l_id = random.choice(loc_ids)

            # Szybkie szukanie unikalnej pary
            while (u_id, l_id) in existing_pairs:
                u_id = random.choice(user_ids)
                l_id = random.choice(loc_ids)

            existing_pairs.add((u_id, l_id))

            val = random.choices([1, 2, 3, 4, 5], weights=[10, 15, 30, 25, 20], k=1)[0]
            priv = random.choice(['public', 'private'])
            fake_date = now - timedelta(days=random.randint(0, 365), seconds=random.randint(0, 86400))

            emotions_batch.append(EmotionPoint(
                user_id=u_id,
                location_id=l_id,
                emotional_value=val,
                privacy_status=priv,
                created_at=fake_date
            ))

            if len(emotions_batch) >= BATCH_SIZE:
                EmotionPoint.objects.bulk_create(emotions_batch)
                total_created_emotions += len(emotions_batch)
                emotions_batch = []
                print(f"  -> Zapisano {total_created_emotions} / {emotions_count} opinii...")

        if emotions_batch:
            EmotionPoint.objects.bulk_create(emotions_batch)
            total_created_emotions += len(emotions_batch)
            print(f"  -> Zapisano {total_created_emotions} / {emotions_count} opinii...")

        # Przywracamy normalne działanie pola w Django
        created_at_field.auto_now_add = True

    end_time = time.time()
    elapsed_time = round(end_time - start_time, 2)
    print("\n" + "🎉" * 15)
    print(f" ZAKOŃCZONO W {elapsed_time} SEKUND! ")
    print("🎉" * 15 + "\n")


if __name__ == '__main__':
    main()