from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from onikisepet.models import Profile

DATA_ENTRY_GROUP = "Data Entry"
VIEWER_GROUP = "Viewer"


class Command(BaseCommand):
    help = "Mevcut kullanıcı gruplarından Profile kayıtları oluşturur."

    def handle(self, *args, **options):
        user_model = get_user_model()
        created_count = 0

        for user in user_model.objects.filter(is_superuser=False):
            if Profile.objects.filter(user=user).exists():
                continue

            if user.groups.filter(name=DATA_ENTRY_GROUP).exists():
                role = Profile.Role.DATA_ENTRY
            elif user.groups.filter(name=VIEWER_GROUP).exists():
                role = Profile.Role.VIEWER
            else:
                continue

            Profile.objects.create(user=user, role=role)
            created_count += 1
            self.stdout.write(f"Oluşturuldu: {user.username} ({role})")

        self.stdout.write(self.style.SUCCESS(f"Toplam {created_count} profil oluşturuldu."))
