from django.core.management.base import BaseCommand

from onikisepet.usecases.profile_sync import sync_all_profiles_from_groups


class Command(BaseCommand):
    help = "Grup üyeliklerine göre Profile kayıtlarını oluşturur veya günceller."

    def handle(self, *args, **options):
        synced_profiles = sync_all_profiles_from_groups()

        self.stdout.write(
            self.style.SUCCESS(
                f"Senkronize edilen profil sayısı: {len(synced_profiles)}"
            )
        )
