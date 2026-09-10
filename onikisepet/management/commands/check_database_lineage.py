from django.core.management.base import BaseCommand, CommandError

from onikisepet.usecases.database_lineage import (
    ForeignLineageError,
    check_database_lineage,
)


class Command(BaseCommand):
    help = (
        'Refuse to proceed if the database belongs to a different migration '
        'lineage. Run this before migrate, not after.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default='default',
            help='Database alias to check. Defaults to "default".',
        )

    def handle(self, *args, **options):
        from django.db import connections

        connection = connections[options['database']]

        try:
            check_database_lineage(using=connection)
        except ForeignLineageError as error:
            # CommandError exits non-zero, which is what stops the Cloud Build
            # step before the migrate step runs.
            raise CommandError(str(error)) from error

        if options['verbosity']:
            self.stdout.write(
                self.style.SUCCESS(
                    'Database lineage matches this branch. Safe to migrate.'
                )
            )
