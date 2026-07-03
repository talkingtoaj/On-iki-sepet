from django.core.management.base import BaseCommand

from onikisepet.bootstrap import bootstrap_kut


class Command(BaseCommand):
    help = (
        "KUT finans uygulaması için ilk kurulum: gruplar, profiller, "
        "hesaplar ve kategoriler."
    )

    def handle(self, *args, **options):
        result = bootstrap_kut()

        if result["groups_created"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Oluşturulan grup sayısı: {result['groups_created']}"
                )
            )
        else:
            self.stdout.write("Oluşturulan grup sayısı: 0")

        self.stdout.write(
            f"Senkronize edilen profil sayısı: {result['profiles_synced']}"
        )

        if result["accounts_created"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Oluşturulan hesap sayısı: {result['accounts_created']}"
                )
            )
        else:
            self.stdout.write("Oluşturulan hesap sayısı: 0")

        if result["categories_created"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Oluşturulan kategori sayısı: {result['categories_created']}"
                )
            )
        else:
            self.stdout.write("Oluşturulan kategori sayısı: 0")

        self.stdout.write(self.style.SUCCESS("İlk kurulum tamamlandı."))
