from django.apps import AppConfig


class AlertEngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.alert_engine'

    def ready(self):
        from . import signals
