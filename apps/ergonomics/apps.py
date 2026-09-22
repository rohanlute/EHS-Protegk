from django.apps import AppConfig


class ErgonomicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ergonomics"
    verbose_name = "Ergonomics Management"

    def ready(self):
        from . import signals  # noqa: F401