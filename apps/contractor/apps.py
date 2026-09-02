from django.apps import AppConfig


class ContractorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contractor'  # This must match the import path
    verbose_name = 'Contractor Management'