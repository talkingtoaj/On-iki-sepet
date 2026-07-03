from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from onikisepet.bootstrap import DEFAULT_GROUPS, create_default_groups


class Command(BaseCommand):
    help = "Varsayılan kullanıcı gruplarını oluşturur."

    def handle(self, *args, **options):
        existing_before = set(
            Group.objects.filter(name__in=DEFAULT_GROUPS).values_list("name", flat=True)
        )
        create_default_groups()

        for name in DEFAULT_GROUPS:
            if name in existing_before:
                self.stdout.write(f"Zaten var: {name}")
            else:
                self.stdout.write(self.style.SUCCESS(f"Oluşturuldu: {name}"))
