import os
import sys
import django

# 1. Automatycznie znajdujemy główny folder projektu
current_dir = os.path.dirname(os.path.abspath(__file__))
while current_dir != '/' and 'manage.py' not in os.listdir(current_dir):
    current_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 2. Automatycznie wyciągamy ustawienia z manage.py
settings_module = None
manage_path = os.path.join(current_dir, 'manage.py')
if os.path.exists(manage_path):
    with open(manage_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'DJANGO_SETTINGS_MODULE' in line and ',' in line:
                parts = line.split(',')
                if len(parts) > 1:
                    settings_module = parts[1].strip(" '\"\n)")
                    break

if settings_module:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
else:
    print("❌ BŁĄD: Nie udało się odczytać nazwy ustawień z pliku manage.py!")
    sys.exit(1)

# 3. Uruchamiamy środowisko Django
django.setup()

from django.db import connection
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db.models import Q
from map.models import Location
from emotions.models import EmotionPoint, Comment


def clear_database():
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("⚠️  UWAGA: NARZĘDZIE DO CZYSZCZENIA BAZY BIG DATA")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    User = get_user_model()

    loc_count = Location.objects.count()
    emo_count = EmotionPoint.objects.count()
    com_count = Comment.objects.count()

    # 4. Identyfikujemy "sztucznych" użytkowników.
    # Zakładamy, że stare boty nazywały się "user_X", a nowe "mass_user_X".
    # Jednocześnie kategorycznie wykluczamy adminów i obsługę (is_superuser / is_staff).
    fake_users = User.objects.filter(
        Q(username__startswith='mass_user') |
        Q(username__startswith='user_')
    ).exclude(is_superuser=True).exclude(is_staff=True)

    fake_users_count = fake_users.count()
    real_users_count = User.objects.count() - fake_users_count

    print(f"Ten skrypt usunie błyskawicznie:")
    print(f"- Lokalizacje: {loc_count}")
    print(f"- Punkty emocji: {emo_count}")
    print(f"- Komentarze: {com_count}")
    print(f"- Sztucznych użytkowników (boty): {fake_users_count}")
    print(f"\n🛡️ Zostaną w pełni ZACHOWANI Twoi prawdziwi użytkownicy: {real_users_count} kont(a).")
    print()

    confirm = input("Czy na pewno chcesz usunąć te dane? Napisz 'TAK' aby potwierdzić: ")

    if confirm == 'TAK':
        print("\nUsuwanie metodą TRUNCATE (Lokalizacje i Emocje)...")

        # Pobieramy dokładne nazwy tabel
        loc_table = Location._meta.db_table
        emo_table = EmotionPoint._meta.db_table
        com_table = Comment._meta.db_table
        user_table = User._meta.db_table

        with connection.cursor() as cursor:
            # Prawdziwy TRUNCATE dla milionów opinii i lokalizacji
            cursor.execute(f'TRUNCATE TABLE "{loc_table}" CASCADE;')
            cursor.execute(f'TRUNCATE TABLE "{emo_table}" CASCADE;')
            cursor.execute(f'TRUNCATE TABLE "{com_table}" CASCADE;')

            # Bezpieczny DELETE (a nie Truncate!) dla tabeli Użytkowników
            print("Usuwanie sztucznych użytkowników...")
            cursor.execute(
                f'DELETE FROM "{user_table}" WHERE (username LIKE %s OR username LIKE %s) AND is_superuser = FALSE AND is_staff = FALSE;',
                ['mass_user%', 'user_%']
            )

        print("Czyszczenie pamięci podręcznej Cache (RAM)...")
        cache.clear()

        print("\n✅ Sukces! Baza danych została odciążona, a Twoje prawdziwe konta pozostały nietknięte.")
    else:
        print("\nAnulowano czyszczenie.")


if __name__ == "__main__":
    clear_database()