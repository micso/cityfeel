# Cityfeel

Aplikacja Django do analizy sentymentu i opinii o miastach.

## Wymagania

Przed rozpoczęciem upewnij się, że masz zainstalowane:

- **Docker & Docker Compose** - dla PostgreSQL i aplikacji Django (zalecane)

**LUB** (dla uruchomienia lokalnego bez Dockera):

- **uv** - menedżer pakietów Python (automatycznie zainstaluje Python 3.13)
- **GDAL, GEOS, PROJ** - biblioteki systemowe dla GeoDjango

## Instalacja

### Opcja A: Uruchomienie z Docker (ZALECANE) 🐳

Najłatwiejszy sposób - wszystko działa automatycznie, bez instalacji dodatkowych bibliotek.

#### 1. Sklonuj repozytorium

```bash
git clone <repository-url>
cd cityfeel
```

#### 2. Skonfiguruj zmienne środowiskowe

Skopiuj przykładowy plik środowiskowy i zaktualizuj go swoimi danymi:

```bash
cp .env.example .env
```

Edytuj plik `.env` i ustaw dane dostępowe do bazy danych:

```env
DB_NAME=cityfeel
DB_USER=cityfeel_user
DB_PASSWORD=twoje_bezpieczne_haslo
DB_HOST=localhost
DB_PORT=5432
```

#### 3. Uruchom aplikację

Zbuduj i uruchom kontenery (PostgreSQL + Django):

```bash
docker compose up --build
```

Aplikacja będzie dostępna pod adresem: `http://127.0.0.1:8000/`

#### 4. Wykonaj migracje (tylko przy pierwszym uruchomieniu)

W nowym terminalu:

```bash
docker compose exec web uv run cityfeel/manage.py migrate
```

#### 5. Utwórz superużytkownika (opcjonalnie)

```bash
docker compose exec web uv run cityfeel/manage.py createsuperuser
```

Panel administracyjny: `http://127.0.0.1:8000/admin/`

---

### Opcja B: Uruchomienie lokalne (bez Dockera)

⚠️ **Wymaga instalacji bibliotek systemowych GDAL, GEOS, PROJ**

#### 1. Sklonuj repozytorium

```bash
git clone <repository-url>
cd cityfeel
```

#### 2. Zainstaluj biblioteki systemowe GeoDjango

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev binutils
```

**macOS:**
```bash
brew install gdal geos proj
```

#### 3. Skonfiguruj zmienne środowiskowe

```bash
cp .env.example .env
```

Edytuj `.env`:

```env
DB_NAME=cityfeel
DB_USER=cityfeel_user
DB_PASSWORD=twoje_bezpieczne_haslo
DB_HOST=localhost
DB_PORT=5432
```

#### 4. Zainstaluj zależności Python

```bash
uv sync
```

#### 5. Uruchom bazę danych PostgreSQL

```bash
docker compose up postgres -d
```

#### 6. Wykonaj migracje

```bash
uv run cityfeel/manage.py migrate
```

#### 7. Utwórz superużytkownika

```bash
uv run cityfeel/manage.py createsuperuser
```

#### 8. Uruchom serwer deweloperski

```bash
uv run cityfeel/manage.py runserver
```

Aplikacja będzie dostępna pod adresem: `http://127.0.0.1:8000/`

Panel administracyjny: `http://127.0.0.1:8000/admin/`

## Przydatne komendy

### Docker - zarządzanie aplikacją

```bash
# Uruchom wszystkie kontenery (PostgreSQL + Django)
docker compose up

# Uruchom w tle
docker compose up -d

# Przebuduj obrazy i uruchom
docker compose up --build

# Zatrzymaj wszystkie kontenery
docker compose down

# Zatrzymaj i usuń wszystkie dane (UWAGA: usuwa dane z bazy!)
docker compose down -v

# Zobacz logi
docker compose logs -f

# Zobacz logi tylko Django
docker compose logs -f web

# Zobacz logi tylko PostgreSQL
docker compose logs -f postgres

# Uruchom tylko bazę danych
docker compose up postgres -d
```

### Docker - komendy Django

```bash
# Uruchom migracje
docker compose exec web uv run cityfeel/manage.py migrate

# Utwórz migracje po zmianach w modelach
docker compose exec web uv run cityfeel/manage.py makemigrations

# Utwórz superużytkownika
docker compose exec web uv run cityfeel/manage.py createsuperuser

# Uruchom shell Django
docker compose exec web uv run cityfeel/manage.py shell

# Uruchom testy
docker compose exec web uv run cityfeel/manage.py test

# Zbierz pliki statyczne
docker compose exec web uv run cityfeel/manage.py collectstatic

# Otwórz bash w kontenerze Django
docker compose exec web bash
```

### Docker - zarządzanie bazą danych

```bash
# Połącz się z bazą PostgreSQL przez psql
docker exec -it cityfeel_postgres psql -U cityfeel_user -d cityfeel
```

### PostGIS

```bash
# Weryfikacja instalacji PostGIS
docker exec cityfeel_postgres psql -U cityfeel_user -d cityfeel -c "SELECT PostGIS_Version();"

# Sprawdzenie zainstalowanych rozszerzeń przestrzennych
docker exec cityfeel_postgres psql -U cityfeel_user -d cityfeel -c "\dx"
```

### Komendy Django (uruchomienie lokalne bez Dockera)

```bash
# Utwórz nową aplikację Django
uv run cityfeel/manage.py startapp <nazwa_aplikacji>

# Utwórz migracje po zmianach w modelach
uv run cityfeel/manage.py makemigrations

# Zastosuj migracje
uv run cityfeel/manage.py migrate

# Utwórz superużytkownika
uv run cityfeel/manage.py createsuperuser

# Uruchom serwer deweloperski
uv run cityfeel/manage.py runserver

# Uruchom testy
uv run cityfeel/manage.py test

# Zbierz pliki statyczne
uv run cityfeel/manage.py collectstatic
```

## Technologie

Ten projekt wykorzystuje:
- **Django 5.2.7** - Framework webowy
- **GeoDjango** - Rozszerzenie Django dla danych geograficznych
- **PostgreSQL 16 z PostGIS 3.6** - Baza danych z rozszerzeniem przestrzennym
- **Docker & Docker Compose** - Konteneryzacja aplikacji
- **uv** - Szybki menedżer pakietów Python
- **Pillow** - Obsługa obrazów (avatary użytkowników)
- **psycopg2** - Adapter PostgreSQL dla Python
- **python-dotenv** - Zarządzanie zmiennymi środowiskowymi