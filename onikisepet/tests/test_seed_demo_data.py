from django.test import TestCase

from onikisepet.demo_data import DEMO_DESCRIPTION_PREFIX, seed_demo_data
from onikisepet.models import Transaction

from .helpers import TransactionTestMixin


class SeedDemoDataTests(TransactionTestMixin, TestCase):
    def test_seed_creates_approved_and_pending_demo_transactions(self):
        result = seed_demo_data()

        self.assertFalse(result["skipped"])
        self.assertGreater(result["created"], 10)
        demo_qs = Transaction.objects.filter(
            description__startswith=DEMO_DESCRIPTION_PREFIX,
        )
        self.assertEqual(demo_qs.count(), result["created"])
        self.assertTrue(
            demo_qs.filter(approval_status=Transaction.ApprovalStatus.APPROVED).exists()
        )
        self.assertTrue(
            demo_qs.filter(approval_status=Transaction.ApprovalStatus.PENDING).exists()
        )
        self.assertTrue(
            demo_qs.filter(
                transaction_type=Transaction.TransactionType.INCOME,
                target_account__currency="USD",
            ).exists()
        )
        self.assertTrue(
            demo_qs.filter(
                transaction_type=Transaction.TransactionType.EXPENSE,
                source_account__currency="EUR",
            ).exists()
        )

    def test_seed_is_idempotent_without_reset(self):
        first = seed_demo_data()
        second = seed_demo_data()

        self.assertFalse(first["skipped"])
        self.assertTrue(second["skipped"])
        self.assertEqual(
            Transaction.objects.filter(
                description__startswith=DEMO_DESCRIPTION_PREFIX,
            ).count(),
            first["created"],
        )

    def test_seed_reset_recreates_demo_transactions(self):
        first = seed_demo_data()
        result = seed_demo_data(reset=True)

        self.assertEqual(result["cleared"], first["created"])
        self.assertEqual(result["created"], first["created"])
        self.assertEqual(
            Transaction.objects.filter(
                description__startswith=DEMO_DESCRIPTION_PREFIX,
            ).count(),
            first["created"],
        )
