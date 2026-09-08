from django.apps import AppConfig


class ToolboxTalkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.toolbox_talk'

    def ready(self):
        from . import signals  # noqa: F401
