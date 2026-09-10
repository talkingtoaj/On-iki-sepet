from django.core.management.base import BaseCommand

from onikisepet.kut_data import KUT_ACCOUNTS, KUT_CATEGORIES, seed_kut_data


class Command(BaseCommand):
    help = "Create KUT church's chart of accounts and categories. Safe to re-run."

    def handle(self, *args, **options):
        created = seed_kut_data()

        if options["verbosity"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Accounts: {created['accounts']} created, "
                    f"{len(KUT_ACCOUNTS) - created['accounts']} already present"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Categories: {created['categories']} created, "
                    f"{len(KUT_CATEGORIES) - created['categories']} already present"
                )
            )
