from django.core.management.base import BaseCommand

from onikisepet.kut_accounts import KUT_ACCOUNTS, load_kut_accounts


class Command(BaseCommand):
    help = "KUT kilisesi için varsayılan hesapları oluşturur."

    def handle(self, *args, **options):
        created_count = load_kut_accounts()
        existing_count = len(KUT_ACCOUNTS) - created_count

        if created_count:
            self.stdout.write(
                self.style.SUCCESS(f"Oluşturulan hesap sayısı: {created_count}")
            )
        if existing_count:
            self.stdout.write(f"Zaten mevcut hesap sayısı: {existing_count}")
