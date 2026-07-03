from django.core.management.base import BaseCommand

from onikisepet.kut_categories import KUT_CATEGORIES, load_kut_categories


class Command(BaseCommand):
    help = "KUT kilisesi için varsayılan gelir ve gider kategorilerini oluşturur."

    def handle(self, *args, **options):
        created_count = load_kut_categories()
        existing_count = len(KUT_CATEGORIES) - created_count

        if created_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Oluşturulan kategori sayısı: {created_count}"
                )
            )
        if existing_count:
            self.stdout.write(
                f"Zaten mevcut kategori sayısı: {existing_count}"
            )
