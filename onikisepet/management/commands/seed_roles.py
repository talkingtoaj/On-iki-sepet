from django.core.management.base import BaseCommand

from onikisepet.usecases.roles import ROLE_PERMISSIONS, seed_roles


class Command(BaseCommand):
    help = "Create the Treasurer, Data Entry and Viewer roles with their permissions."

    def handle(self, *args, **options):
        seed_roles()

        if options["verbosity"]:
            for role, codenames in ROLE_PERMISSIONS.items():
                self.stdout.write(
                    self.style.SUCCESS(f"{role}: {len(codenames)} permissions")
                )
