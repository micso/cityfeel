#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cityfeel.settings')

    # --- FIX STRUKTURY PROJEKTU ---
    # Python musi widzieć foldery w dwóch miejscach:

    # 1. Żeby widział to co jest głęboko ('auth', 'map', 'emotions' i same ustawienia 'cityfeel')
    sys.path.insert(0, '/app/cityfeel')

    # 2. Żeby widział to co jest na wierzchu (nowa apka 'social' i sam 'manage.py')
    sys.path.insert(0, '/app')
    # ------------------------------

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()