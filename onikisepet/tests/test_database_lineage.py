"""The guard that refuses to migrate a database from another lineage.

The failure this protects against is not a crash but a half-migrated
production database, so the guard has to be right about three things: it must
allow a fresh database, allow our own lineage, and refuse a foreign one. All
three are asserted here.
"""

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from onikisepet.usecases.database_lineage import (
    ForeignLineageError,
    check_database_lineage,
    find_foreign_migrations,
    known_migration_names,
)

# Names taken from the collaborator's lineage. These share numbers with ours
# but not names, which is the whole reason migrate does not skip them.
FOREIGN_NAMES = [
    "0007_auditlog",
    "0008_transaction_approval",
    "0009_profile",
    "0010_receipt_file_type",
    "0011_bank_statement_import",
    "0020_bankstatementrow_is_incoming_transfer",
]

OUR_NAMES = [
    "0001_initial",
    "0006_receipt",
    "0007_exchangerate",
    "0011_bankstatementimport_bankstatementrow",
]


@override_settings(LANGUAGE_CODE="en")
class FindForeignMigrationTests(TestCase):
    def test_fresh_database_has_nothing_foreign(self):
        self.assertEqual(find_foreign_migrations(set(), OUR_NAMES), [])

    def test_our_own_lineage_is_not_foreign(self):
        self.assertEqual(find_foreign_migrations(OUR_NAMES, OUR_NAMES), [])

    def test_collaborator_lineage_is_foreign(self):
        found = find_foreign_migrations(FOREIGN_NAMES, OUR_NAMES)

        self.assertEqual(found, sorted(FOREIGN_NAMES))

    def test_shared_ancestor_alone_is_not_foreign(self):
        # 0006 is the common ancestor and is applied in both lineages, so it
        # must not be what trips the guard.
        self.assertEqual(find_foreign_migrations(["0006_receipt"], OUR_NAMES), [])

    def test_a_single_foreign_migration_is_enough(self):
        # The deployed database would be caught by any one of these, but the
        # realistic partial case is a deploy that already failed part way.
        applied = OUR_NAMES + ["0009_profile"]

        self.assertEqual(find_foreign_migrations(applied, OUR_NAMES), ["0009_profile"])

    def test_result_is_sorted_for_a_stable_message(self):
        found = find_foreign_migrations(["0020_z", "0007_a", "0009_m"], [])

        self.assertEqual(found, ["0007_a", "0009_m", "0020_z"])


@override_settings(LANGUAGE_CODE="en")
class KnownMigrationNameTests(TestCase):
    def test_our_migrations_are_discovered_from_disk(self):
        known = known_migration_names()

        self.assertIn("0006_receipt", known)
        self.assertIn("0007_exchangerate", known)
        self.assertIn("0011_bankstatementimport_bankstatementrow", known)

    def test_the_collaborator_migrations_are_not_on_our_disk(self):
        known = known_migration_names()

        for name in FOREIGN_NAMES:
            self.assertNotIn(name, known)

    def test_lineage_ends_at_0011(self):
        # If someone adds 0012 here, the renumbering question is back open and
        # this test should be updated deliberately rather than drift.
        numbers = sorted(name.split("_")[0] for name in known_migration_names())

        self.assertEqual(numbers[-1], "0011")


@override_settings(LANGUAGE_CODE="en")
class ForeignLineageErrorTests(TestCase):
    def test_message_names_every_offending_migration(self):
        error = ForeignLineageError(["0009_profile", "0007_auditlog"])

        for name in ["0009_profile", "0007_auditlog"]:
            self.assertIn(name, str(error))

    def test_message_points_at_the_runbook(self):
        error = ForeignLineageError(["0009_profile"])

        self.assertIn("docs/deployment/runbook.md", str(error))

    def test_message_explains_the_half_migrated_risk(self):
        # The operator reading this in Cloud Build logs needs to know why it
        # refused, not just that it did.
        message = str(ForeignLineageError(["0009_profile"]))

        self.assertIn("half-migrated", message)


@override_settings(LANGUAGE_CODE="en")
class CheckDatabaseLineageTests(TestCase):
    def test_the_test_database_passes(self):
        # The test database is built from our own migrations, so it stands in
        # for a correctly provisioned one.
        self.assertEqual(check_database_lineage(), [])

    def test_command_succeeds_on_our_own_database(self):
        call_command("check_database_lineage", verbosity=0)

    def test_command_raises_on_a_foreign_database(self):
        from django.db.migrations.recorder import MigrationRecorder

        # Record a migration this lineage does not have, exactly as the
        # collaborator's database would have it.
        MigrationRecorder.Migration.objects.create(
            app="onikisepet", name="0009_profile"
        )

        with self.assertRaises(CommandError) as caught:
            call_command("check_database_lineage", verbosity=0)

        self.assertIn("0009_profile", str(caught.exception))
        self.assertIn("different migration lineage", str(caught.exception))
