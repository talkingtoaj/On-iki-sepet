from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from onikisepet.permissions import APPROVER_GROUP, DATA_ENTRY_GROUP, VIEWER_GROUP
from onikisepet.usecases.profile_sync import sync_user_profile_from_groups

DEMO_PASSWORD = "DemoPass123!"

DEMO_USERS = (
    {
        "username": "finans",
        "email": "finans@example.com",
        "groups": (DATA_ENTRY_GROUP,),
    },
    {
        "username": "onaylayici",
        "email": "onaylayici@example.com",
        "groups": (DATA_ENTRY_GROUP, APPROVER_GROUP),
    },
    {
        "username": "lider",
        "email": "lider@example.com",
        "groups": (VIEWER_GROUP,),
    },
)


def create_demo_users(*, reset_passwords=False):
    user_model = get_user_model()
    created_count = 0
    updated_count = 0

    for spec in DEMO_USERS:
        user, created = user_model.objects.get_or_create(
            username=spec["username"],
            defaults={"email": spec["email"]},
        )
        if created:
            created_count += 1
        elif user.email != spec["email"]:
            user.email = spec["email"]
            user.save(update_fields=["email"])
            updated_count += 1

        user.groups.set(
            Group.objects.filter(name__in=spec["groups"]),
        )
        sync_user_profile_from_groups(user)

        if created or reset_passwords:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])

    return {
        "created_count": created_count,
        "updated_count": updated_count,
    }


class Command(BaseCommand):
    help = (
        "MVP demo kullanıcılarını oluşturur: finans, onaylayici, lider. "
        "Gruplar yoksa önce create_default_groups çalıştırın."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Mevcut demo kullanıcıların şifresini sıfırla.",
        )

    def handle(self, *args, **options):
        result = create_demo_users(reset_passwords=options["reset_passwords"])

        if result["created_count"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Oluşturulan demo kullanıcı sayısı: {result['created_count']}"
                )
            )
        else:
            self.stdout.write("Oluşturulan demo kullanıcı sayısı: 0")

        if result["updated_count"]:
            self.stdout.write(
                f"Güncellenen e-posta sayısı: {result['updated_count']}"
            )

        for spec in DEMO_USERS:
            groups = ", ".join(spec["groups"])
            self.stdout.write(f"  {spec['username']} ({groups})")

        self.stdout.write(f"Demo şifresi: {DEMO_PASSWORD}")
        self.stdout.write(self.style.SUCCESS("Demo kullanıcıları hazır."))
