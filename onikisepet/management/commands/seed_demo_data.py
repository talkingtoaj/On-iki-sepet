from django.core.management.base import BaseCommand

from onikisepet.demo_data import seed_demo_data


class Command(BaseCommand):
    help = (
        "Sunum için dashboard ve raporları dolduran örnek işlemleri oluşturur. "
        "Önce bootstrap_kut ve demo kullanıcıları kurar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Mevcut [Demo] işlemlerini silip yeniden oluştur.",
        )

    def handle(self, *args, **options):
        result = seed_demo_data(reset=options["reset"])

        if result["skipped"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Zaten {result['existing']} demo işlem var. "
                    "Yenilemek için --reset kullanın."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo veri hazır: {result['created']} işlem "
                f"(kullanıcı: {result['user']}, silinen: {result['cleared']})."
            )
        )
        self.stdout.write(
            "Giriş: finans / DemoPass123!  |  admin / qweqweqwe (bootstrap ile)"
        )
