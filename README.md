# Cityfeel

Aplikacja Django do analizy sentymentu i opinii o miastach.

## Wymagania

Przed rozpoczęciem upewnij się, że masz zainstalowane:

- **Docker & Docker Compose** - dla bazy danych PostgreSQL
- **uv** - menedżer pakietów Python (automatycznie zainstaluje Python 3.13)

## Instalacja

Wykonaj poniższe kroki, aby skonfigurować projekt na swoim komputerze:

### 1. Sklonuj repozytorium

```bash
git clone <repository-url>
cd cityfeel
```

### 2. Skonfiguruj zmienne środowiskowe

Skopiuj przykładowy plik środowiskowy i zaktualizuj go swoimi danymi:

```bash
cp .env.example .env
```

Edytuj plik `.env` i ustaw dane dostępowe do bazy danych:

```env
POSTGRES_DB=cityfeel
POSTGRES_USER=cityfeel_user
POSTGRES_PASSWORD=twoje_bezpieczne_haslo

DB_NAME=cityfeel
DB_USER=cityfeel_user
DB_PASSWORD=twoje_bezpieczne_haslo
DB_HOST=localhost
DB_PORT=5432
```

### 3. Zainstaluj zależności Python

```bash
uv sync
```

### 4. Uruchom bazę danych PostgreSQL

Uruchom kontener PostgreSQL w tle:

```bash
docker-compose up -d
```

Sprawdź, czy baza danych działa:

```bash
docker-compose ps
```

### 5. Wykonaj migracje bazy danych

```bash
python cityfeel/manage.py migrate
```

### 6. Utwórz superużytkownika (opcjonalnie)

Aby uzyskać dostęp do panelu administracyjnego Django:

```bash
python cityfeel/manage.py createsuperuser
```

### 7. Uruchom serwer deweloperski

```bash
python cityfeel/manage.py runserver
```

Aplikacja będzie dostępna pod adresem: `http://127.0.0.1:8000/`

Panel administracyjny: `http://127.0.0.1:8000/admin/`

## Przydatne komendy

### Zarządzanie Docker i bazą danych

```bash
# Zatrzymaj bazę danych
docker-compose down

# Zatrzymaj i usuń wszystkie dane (UWAGA: usuwa wszystkie dane z bazy!)
docker-compose down -v

# Zobacz logi PostgreSQL
docker-compose logs -f postgres

# Połącz się z bazą PostgreSQL przez psql
docker exec -it cityfeel_postgres psql -U cityfeel_user -d cityfeel
```

### Komendy Django

```bash
# Utwórz nową aplikację Django
python cityfeel/manage.py startapp <nazwa_aplikacji>

# Utwórz migracje po zmianach w modelach
python cityfeel/manage.py makemigrations

# Zastosuj migracje
python cityfeel/manage.py migrate

# Utwórz superużytkownika
python cityfeel/manage.py createsuperuser

# Uruchom serwer deweloperski
python cityfeel/manage.py runserver

# Uruchom testy
python cityfeel/manage.py test

# Zbierz pliki statyczne
python cityfeel/manage.py collectstatic
```

## Technologie

Ten projekt wykorzystuje:
- **Django 5.2.7** - Framework webowy
- **PostgreSQL 16** - Baza danych
- **psycopg2** - Adapter PostgreSQL dla Python
- **python-dotenv** - Zarządzanie zmiennymi środowiskowymi