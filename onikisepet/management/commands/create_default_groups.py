from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = "Varsayılan kullanıcı gruplarını oluşturur."

    def handle(self, *args, **options):
        for name in ("Data Entry", "Viewer"):
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Oluşturuldu: {name}"))
            else:
                self.stdout.write(f"Zaten var: {name}")
