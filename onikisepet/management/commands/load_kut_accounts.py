from django.core.management.base import BaseCommand

from onikisepet.kut_accounts import seed_kut_accounts


class Command(BaseCommand):
    help = "KUT Kilisesi hesap yapısını veritabanına yükler."

    def handle(self, *args, **options):
        created, existing = seed_kut_accounts()

        for account in created:
            self.stdout.write(self.style.SUCCESS(f"Oluşturuldu: {account.name}"))

        for account in existing:
            self.stdout.write(f"Zaten var: {account.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamamlandı. {len(created)} yeni, {len(existing)} mevcut hesap."
            )
        )
