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
uv run cityfeel/manage.py test
uv run cityfeel/manage.py shell
```

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
