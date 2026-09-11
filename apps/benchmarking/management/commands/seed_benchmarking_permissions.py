from django.core.management.base import BaseCommand
from apps.accounts.models import Permissions
from apps.benchmarking.constants import PERMISSIONS


class Command(BaseCommand):
    help = "Create or update the Site / Plant Benchmarking permission catalogue."

    def handle(self, *args, **options):
        for code, (name, permission_type) in PERMISSIONS.items():
            Permissions.objects.update_or_create(code=code, defaults={"name": name, "module": "BENCHMARKING", "permission_type": permission_type})
        self.stdout.write(self.style.SUCCESS("Benchmarking permissions are ready. Assign them to existing roles in Role Management."))
