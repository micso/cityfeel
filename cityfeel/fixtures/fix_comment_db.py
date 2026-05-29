import os
import sys
import django
from django.db import connection

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cityfeel.settings')
django.setup()

def main():
    try:
        with connection.cursor() as cursor:
            cursor.execute('ALTER TABLE emotions_comment ALTER COLUMN is_hidden DROP NOT NULL;')
        print("✅ Baza danych naprawiona! Blokada z tabeli komentarzy zdjęta.")
    except Exception as e:
        print(f"❌ Wystąpił błąd: {e}")

if __name__ == '__main__':
    main()