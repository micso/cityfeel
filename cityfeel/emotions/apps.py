from django.apps import AppConfig


class EmotionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emotions'

    def ready(self):
        import emotions.signals  # noqa: F401
