from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from onikisepet.bootstrap import (
    DEFAULT_SUPERUSER_PASSWORD,
    DEFAULT_SUPERUSER_USERNAME,
    bootstrap_kut,
    create_default_groups,
    create_default_superuser,
)
from onikisepet.kut_accounts import KUT_ACCOUNTS
from onikisepet.kut_categories import KUT_CATEGORIES
from onikisepet.models import Account, Category, Profile
from onikisepet.permissions import APPROVER_GROUP, DATA_ENTRY_GROUP, VIEWER_GROUP

from .helpers import ProfileTestMixin, TransactionTestMixin


class BootstrapKutTests(ProfileTestMixin, TransactionTestMixin, TestCase):
    def test_create_default_groups_creates_data_entry_viewer_and_approver(self):
        Group.objects.all().delete()

        created_count = create_default_groups()

        self.assertEqual(created_count, 3)
        self.assertTrue(Group.objects.filter(name=DATA_ENTRY_GROUP).exists())
        self.assertTrue(Group.objects.filter(name=VIEWER_GROUP).exists())
        self.assertTrue(Group.objects.filter(name=APPROVER_GROUP).exists())

    def test_create_default_groups_is_idempotent(self):
        create_default_groups()

        created_count = create_default_groups()

        self.assertEqual(created_count, 0)
        self.assertEqual(Group.objects.count(), 3)

    def test_create_default_superuser_creates_admin_user(self):
        user_model = get_user_model()
        user_model.objects.filter(username=DEFAULT_SUPERUSER_USERNAME).delete()

        created_count = create_default_superuser()

        admin_user = user_model.objects.get(username=DEFAULT_SUPERUSER_USERNAME)

        self.assertEqual(created_count, 1)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(
            admin_user.check_password(DEFAULT_SUPERUSER_PASSWORD),
        )

    def test_create_default_superuser_is_idempotent(self):
        create_default_superuser()

        created_count = create_default_superuser()

        self.assertEqual(created_count, 0)
        self.assertEqual(
            get_user_model().objects.filter(username=DEFAULT_SUPERUSER_USERNAME).count(),
            1,
        )

    def test_bootstrap_kut_creates_groups_accounts_and_categories(self):
        bootstrap_kut()

        self.assertTrue(Group.objects.filter(name=DATA_ENTRY_GROUP).exists())
        self.assertTrue(Group.objects.filter(name=VIEWER_GROUP).exists())
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))

    def test_bootstrap_kut_syncs_profiles_for_grouped_users(self):
        data_entry_user = self.create_user("bootstrap_data_entry", group_name=DATA_ENTRY_GROUP)
        viewer_user = self.create_user("bootstrap_viewer", group_name=VIEWER_GROUP)
        groupless_user = self.create_user("bootstrap_groupless")

        bootstrap_kut()

        self.assertEqual(
            Profile.objects.get(user=data_entry_user).role,
            Profile.Role.DATA_ENTRY,
        )
        self.assertEqual(
            Profile.objects.get(user=viewer_user).role,
            Profile.Role.VIEWER,
        )
        self.assertFalse(Profile.objects.filter(user=groupless_user).exists())

    def test_bootstrap_kut_returns_step_counts(self):
        Group.objects.all().delete()
        Account.objects.all().delete()
        Category.objects.all().delete()
        get_user_model().objects.filter(username=DEFAULT_SUPERUSER_USERNAME).delete()

        result = bootstrap_kut()

        self.assertEqual(result["groups_created"], 3)
        self.assertEqual(result["profiles_synced"], 0)
        self.assertEqual(result["accounts_created"], len(KUT_ACCOUNTS))
        self.assertEqual(result["categories_created"], len(KUT_CATEGORIES))
        self.assertEqual(result["superuser_created"], 1)

    def test_bootstrap_kut_is_idempotent_for_seed_data(self):
        bootstrap_kut()

        result = bootstrap_kut()

        self.assertEqual(result["groups_created"], 0)
        self.assertEqual(result["accounts_created"], 0)
        self.assertEqual(result["categories_created"], 0)
        self.assertEqual(result["superuser_created"], 0)
        self.assertEqual(Group.objects.count(), 3)
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))


class BootstrapKutCommandTests(TestCase):
    def test_command_runs_initial_setup_and_reports_summary(self):
        Group.objects.all().delete()
        Account.objects.all().delete()
        Category.objects.all().delete()
        get_user_model().objects.filter(username=DEFAULT_SUPERUSER_USERNAME).delete()
        stdout = StringIO()

        call_command("bootstrap_kut", stdout=stdout)
        output = stdout.getvalue()

        self.assertEqual(Group.objects.count(), 3)
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))
        self.assertIn("İlk kurulum tamamlandı", output)
        self.assertIn("Oluşturulan grup sayısı: 3", output)
        self.assertIn(f"Oluşturulan hesap sayısı: {len(KUT_ACCOUNTS)}", output)
        self.assertIn(
            f"Oluşturulan kategori sayısı: {len(KUT_CATEGORIES)}",
            output,
        )
        self.assertIn("Oluşturulan süper kullanıcı sayısı: 1", output)
        self.assertTrue(
            get_user_model()
            .objects.filter(username=DEFAULT_SUPERUSER_USERNAME, is_superuser=True)
            .exists()
        )

    def test_command_is_idempotent_on_second_run(self):
        call_command("bootstrap_kut", stdout=StringIO())
        stdout = StringIO()

        call_command("bootstrap_kut", stdout=stdout)
        output = stdout.getvalue()

        self.assertIn("İlk kurulum tamamlandı", output)
        self.assertIn("Oluşturulan grup sayısı: 0", output)
        self.assertIn("Oluşturulan hesap sayısı: 0", output)
        self.assertIn("Oluşturulan kategori sayısı: 0", output)
        self.assertIn("Oluşturulan süper kullanıcı sayısı: 0", output)
