from django.apps import AppConfig

class RhBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rhBot'

    def ready(self):
        from . import views