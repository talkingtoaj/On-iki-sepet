"""Refuse to migrate a database that belongs to a different migration lineage.

This branch and the collaborator's diverged from a common ancestor at `0006`.
Migration numbers `0007`-`0011` exist in both lineages describing different
schema changes, and theirs continues to `0020`.

The numbers collide but the names do not, and Django records applied migrations
by name. So `migrate` against the collaborator's database does not skip our
migrations: it applies `0007_exchangerate` onward on top of their schema,
succeeds for the first few, and fails at `0011`, where both lineages declare
`BankStatementImport` and `BankStatementRow` in this app with no `db_table`
override and so want the same two tables.

On PostgreSQL each migration commits in its own transaction, so that failure
arrives after the earlier migrations are already committed. The result is a
production database half-migrated onto a lineage it does not belong to, with
nothing rolled back. `migrate` is the wrong place to find that out, so this
check runs before it and refuses.

The test for "foreign" is deliberately not a hardcoded list of their migration
names. It is any applied migration for this app that has no migration file in
this lineage, so the check keeps working as either side adds migrations.
"""

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

APP_LABEL = 'onikisepet'


class ForeignLineageError(Exception):
    """The database has migrations applied that this lineage does not contain."""

    def __init__(self, foreign_names):
        self.foreign_names = list(foreign_names)
        super().__init__(self._message())

    def _message(self):
        listed = '\n'.join(f'  - {name}' for name in self.foreign_names)
        return (
            f'This database belongs to a different migration lineage. It has '
            f'{len(self.foreign_names)} migration(s) applied for '
            f'"{APP_LABEL}" that do not exist in this branch:\n'
            f'{listed}\n\n'
            f'Migrating it would apply this lineage on top of a schema built '
            f'by another one. The early migrations would succeed and a later '
            f'one would fail on a table that already exists, leaving the '
            f'database half-migrated with nothing rolled back.\n\n'
            f'This is expected against the deployed database. Point at a '
            f'fresh database, or see "Database lineage" in '
            f'docs/deployment/runbook.md for the cutover procedure.'
        )


def find_foreign_migrations(applied_names, known_names):
    """Applied migrations for this app with no migration file in this lineage.

    Pure set arithmetic so the rule can be tested without a database. An empty
    result means the database is safe to migrate; a fresh database applies
    nothing and so is trivially safe.
    """
    return sorted(set(applied_names) - set(known_names))


def applied_migration_names(using=None):
    """Recorded migration names for this app, empty on a fresh database."""
    recorder = MigrationRecorder(connection if using is None else using)

    # A database that has never been migrated has no recorder table at all.
    # That is the fresh-database case, which is precisely what we want to
    # allow, so it is not an error.
    if not recorder.has_table():
        return set()

    return {
        name
        for app_label, name in recorder.applied_migrations()
        if app_label == APP_LABEL
    }


def known_migration_names():
    """Migration names that exist as files in this lineage."""
    loader = MigrationLoader(None, ignore_no_migrations=True)
    return {
        name
        for app_label, name in loader.disk_migrations
        if app_label == APP_LABEL
    }


def check_database_lineage(using=None):
    """Raise ForeignLineageError if the database is on another lineage."""
    foreign = find_foreign_migrations(
        applied_migration_names(using=using),
        known_migration_names(),
    )

    if foreign:
        raise ForeignLineageError(foreign)

    return foreign
