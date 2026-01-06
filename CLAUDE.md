# Instrukcje dla Claude Code

## Zarządzanie zależnościami i uruchamianie projektu

Ten projekt używa **uv** do zarządzania zależnościami i środowiskiem Python.

### Ważne komendy:

#### Uruchamianie Django
Zawsze używaj `uv run` zamiast `python`:

```bash
# Django management commands
uv run cityfeel/manage.py <command>

# Przykłady:
uv run cityfeel/manage.py check
uv run cityfeel/manage.py migrate
uv run cityfeel/manage.py runserver
uv run cityfeel/manage.py makemigrations
uv run cityfeel/manage.py shell
```

#### Uruchamianie testów
**WAŻNE:** Testy muszą być uruchamiane z podaniem nazwy głównego modułu `cityfeel`:

```bash
# Z głównego katalogu projektu (zalecane dla CI/CD i skryptów)
uv run cityfeel/manage.py test cityfeel

# Alternatywnie: z katalogu cityfeel/ (bez podawania modułu)
cd cityfeel
uv run manage.py test

# Uruchomienie testów konkretnej aplikacji
uv run cityfeel/manage.py test cityfeel.api
uv run cityfeel/manage.py test cityfeel.auth
```

**Dlaczego:** Django szuka testów względem working directory. Uruchamianie `uv run cityfeel/manage.py test` (bez `cityfeel` na końcu) z głównego katalogu projektu nie znajdzie żadnych testów.

#### Instalacja zależności
```bash
uv add <package-name>
```

#### Synchronizacja zależności
```bash
uv sync
```

## Struktura projektu

```
cityfeel/
├── cityfeel/           # Główny katalog Django
│   ├── manage.py       # Django CLI
│   ├── cityfeel/       # Projekt główny (settings, urls)
│   ├── auth/           # Aplikacja autoryzacji (CFUser, login, register, profile)
│   ├── emotions/       # Aplikacja emocji (EmotionPoint)
│   ├── map/            # Aplikacja mapy (Location, emotion_map view)
│   ├── api/            # Aplikacja API
│   └── templates/      # Szablony globalne (base.html)
└── plan.md            # Plan rozwoju aplikacji
```

## Stack technologiczny

- **Backend:** Django 5.2
- **Frontend:** Bootstrap 5.3.0, Leaflet.js
- **Database:** PostgreSQL (z PostGIS)
- **Python:** uv package manager
- **Docker:** docker-compose.yml

## Notatki dla Claude

- Zawsze używaj `uv run` do uruchamiania komend Django
- Projekt używa polskich etykiet i komunikatów
- Style: minimalistyczny design, kolory białe i niebieskie
- Model użytkownika: CFUser (rozszerza AbstractUser)
- Namespace URL dla auth: `cf_auth`

## Model prywatności EmotionPoint

Każdy EmotionPoint ma pole `privacy_status` z dwoma wartościami:
- **public**: Emocja publiczna - widoczna na mapie, w statystykach lokalizacji I na profilu użytkownika (z imieniem i nazwiskiem)
- **private**: Emocja prywatna/anonimowa - widoczna na mapie i w statystykach lokalizacji, ALE NIE na profilu użytkownika (nie można przypisać do konkretnej osoby)

**Ważne**: Wszystkie emocje (publiczne i prywatne) są widoczne na mapie i wpływają na statystyki lokalizacji. Różnica polega tylko na tym, czy pokazujemy autora emocji.
