import os
import sys
import django
import random
from datetime import timedelta

# --- INICJALIZACJA ŚRODOWISKA DJANGO ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cityfeel.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.db import connection
from map.models import Location
from emotions.models import EmotionPoint

User = get_user_model()


def fix_database_sync():
    """
    Automatyczny naprawiacz bazy danych. Jeśli w Postgresie ostała się
    tabela z wymaganą kolumną is_hidden (a w kodzie jej nie ma),
    to wymuszamy usunięcie restrykcji NOT NULL.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE emotions_emotion_point ALTER COLUMN is_hidden DROP NOT NULL;')
    except Exception:
        # Jeśli kolumna nie istnieje, ignorujemy błąd
        pass


def generate_unique_names(count):
    categories = ['Szkoła', 'Park', 'Siłownia', 'Plaża', 'Kawiarnia', 'Restauracja', 'Przystanek', 'Sklep', 'Galeria',
                  'Kino', 'Biblioteka', 'Plac zabaw', 'Boisko', 'Przychodnia', 'Zabytek', 'Pomnik']
    districts = ['w Śródmieściu', 'we Wrzeszczu', 'w Oliwie', 'na Przymorzu', 'w Brzeźnie', 'w Jelitkowie', 'na Zaspie',
                 'na Żabiance', 'w Osowej', 'na Chełmie', 'na Morenie', 'na Oruni', 'na Przeróbce', 'w Letnicy',
                 'w Nowym Porcie', 'na Stogach']

    used_names = set()
    names_list = []

    for _ in range(count):
        while True:
            cat = random.choice(categories)
            dist = random.choice(districts)
            name = f"{cat} {dist}"

            if name in used_names:
                name = f"{cat} {dist} nr {random.randint(1, 9999)}"

            if name not in used_names:
                used_names.add(name)
                names_list.append(name)
                break

    return names_list


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
    print("\n" + "=" * 50)
    print("🏙️  GENERATOR DANYCH DLA GDAŃSKA (CITYFEEL)")
    print("=" * 50)

    # Odpalamy naprawiacz bazy w tle
    fix_database_sync()

    try:
        users_input = input("1. Ile UŻYTKOWNIKÓW wygenerować? (np. 10, wciśnij Enter by pominąć): ")
        users_count = int(users_input) if users_input.strip() else 0

        locs_input = input("2. Ile LOKALIZACJI w Gdańsku dodać? (np. 50, wciśnij Enter by pominąć): ")
        locs_count = int(locs_input) if locs_input.strip() else 0

        emotions_input = input("3. Ile LOSOWYCH OPINII (emocji) rozrzucić? (np. 500, wciśnij Enter by pominąć): ")
        emotions_count = int(emotions_input) if emotions_input.strip() else 0
    except ValueError:
        print("BŁĄD: Wprowadzono niepoprawną wartość. Przerwano.")
        return

    # --- TWORZENIE UŻYTKOWNIKÓW ---
    if users_count > 0:
        print(f"\nTworzenie {users_count} użytkowników...")
        created_users = 0

        # Przygotowanie pliku do zapisu
        users_file_path = os.path.join(current_dir, 'test_users.txt')
        with open(users_file_path, 'a', encoding='utf-8') as f:
            for i in range(users_count):
                username = f"tester_gdansk_{random.randint(1000, 99999)}"
                password = f"HasloTestowe{random.randint(100, 999)}!"

                if not User.objects.filter(username=username).exists():
                    User.objects.create_user(username=username, password=password)
                    created_users += 1
                    f.write(f"Login: {username} | Hasło: {password}\n")

            if (i + 1) % 100 == 0:
                print(f"-> Wygenerowano już {i + 1} z {users_count} użytkowników...")
                
        print(f"✅ Utworzono {created_users} unikalnych kont testowych.")
        print(f"💾 Zapisano dane logowania do pliku: {users_file_path}")

    # --- TWORZENIE LOKALIZACJI ---
    if locs_count > 0:
        print(f"\nTworzenie {locs_count} lokalizacji (wyłącznie na lądzie)...")
        names = generate_unique_names(locs_count)

        for name in names:
            lat, lon = get_random_land_coordinates_in_gdansk()

            Location.objects.create(
                name=name,
                coordinates=Point(lon, lat, srid=4326)
            )
        print(f"✅ Utworzono {locs_count} lokalizacji na mapie.")

    # --- TWORZENIE EMOCJI ---
    if emotions_count > 0:
        print(f"\nTworzenie {emotions_count} losowych opinii z datami z ostatniego roku...")
        users = list(User.objects.all())
        locations = list(Location.objects.all())

        if not users or not locations:
            print("❌ BŁĄD: Aby dodać opinie, w bazie musi być minimum 1 użytkownik i 1 lokalizacja.")
        else:
            now = timezone.now()

            existing_pairs = set(EmotionPoint.objects.all().values_list('user_id', 'location_id'))
            max_possible_combinations = len(users) * len(locations)
            available_slots = max_possible_combinations - len(existing_pairs)

            if emotions_count > available_slots:
                print(f"⚠️ OSTRZEŻENIE: Masz {len(users)} użytkowników i {len(locations)} lokalizacji.")
                print(f"Można wygenerować maksymalnie {available_slots} nowych unikalnych opinii.")
                emotions_count = available_slots

            created_emotions = 0

            for i in range(emotions_count):
                u = None
                l = None

                for _ in range(100):
                    u = random.choice(users)
                    l = random.choice(locations)
                    if (u.id, l.id) not in existing_pairs:
                        break

                if (u.id, l.id) in existing_pairs:
                    break

                existing_pairs.add((u.id, l.id))

                val = random.choices([1, 2, 3, 4, 5], weights=[10, 15, 30, 25, 20], k=1)[0]
                priv = random.choice(['public', 'private'])

                # Zapisujemy nowy punkt emocji
                ep = EmotionPoint.objects.create(
                    user=u,
                    location=l,
                    emotional_value=val,
                    privacy_status=priv
                )

                # Cofa datę
                fake_date = now - timedelta(days=random.randint(0, 365), seconds=random.randint(0, 86400))
                EmotionPoint.objects.filter(pk=ep.pk).update(created_at=fake_date)
                created_emotions += 1

            print(f"✅ Utworzono {created_emotions} unikalnych opinii/emocji.")

    print("\n🎉 ZAKOŃCZONO DZIAŁANIE SKRYPTU!\n")


if __name__ == '__main__':
    main()