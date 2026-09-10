"""Seeding the congregation's chart of accounts.

This is real church configuration, so the seed has to be safe to run against a
live database: it must never duplicate a row, and never overwrite a balance or
a rename the treasurer has made.
"""

from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase, override_settings

from onikisepet.kut_data import KUT_ACCOUNTS, KUT_CATEGORIES, seed_kut_data
from onikisepet.models import Account, Category


@override_settings(LANGUAGE_CODE="en")
class SeedKutDataTests(TestCase):
    def test_seeding_creates_every_account_and_category(self):
        seed_kut_data()

        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))

    def test_the_accounts_match_the_congregation_s_real_names(self):
        seed_kut_data()

        names = set(Account.objects.values_list("name", flat=True))
        self.assertIn("Kasa (Defter)", names)
        self.assertIn("Garanti - Ana Gider", names)
        self.assertIn("Deprem Fonu (EUR)", names)

    def test_foreign_currency_accounts_keep_their_currency(self):
        seed_kut_data()

        self.assertEqual(Account.objects.get(name="Omega (USD)").currency, "USD")
        self.assertEqual(Account.objects.get(name="Merhamet (EUR)").currency, "EUR")

    def test_income_and_expense_categories_are_both_seeded(self):
        seed_kut_data()

        self.assertTrue(Category.objects.filter(category_type="income").exists())
        self.assertTrue(Category.objects.filter(category_type="expense").exists())

    def test_seeding_twice_creates_nothing_the_second_time(self):
        seed_kut_data()
        second = seed_kut_data()

        self.assertEqual(second, {"accounts": 0, "categories": 0})
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
        self.assertEqual(Category.objects.count(), len(KUT_CATEGORIES))

    def test_seeding_does_not_overwrite_an_existing_opening_balance(self):
        """The treasurer's own figures must survive a re-run."""
        seed_kut_data()
        cash = Account.objects.get(name="Kasa (Defter)")
        cash.opening_balance = Decimal("4250.00")
        cash.save()

        seed_kut_data()

        cash.refresh_from_db()
        self.assertEqual(cash.opening_balance, Decimal("4250.00"))

    def test_seeding_alongside_unrelated_accounts_leaves_them_alone(self):
        Account.objects.create(
            name="A Custom Account",
            account_type="bank",
            account_purpose="savings",
            currency="TRY",
        )

        seed_kut_data()

        self.assertTrue(Account.objects.filter(name="A Custom Account").exists())
        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS) + 1)

    def test_seeded_accounts_pass_model_validation(self):
        """get_or_create bypasses save(), so the specs are checked explicitly."""
        seed_kut_data()

        for account in Account.objects.all():
            account.full_clean()

    def test_management_command_seeds_the_data(self):
        call_command("seed_kut_data", verbosity=0)

        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))

    def test_management_command_is_safe_to_re_run(self):
        call_command("seed_kut_data", verbosity=0)
        call_command("seed_kut_data", verbosity=0)

        self.assertEqual(Account.objects.count(), len(KUT_ACCOUNTS))
