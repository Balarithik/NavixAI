"""
Explicit indoor graph import for one building.

    python manage.py import_indoor_data data/8th_block --building-code 8TH_BLOCK
    python manage.py import_indoor_data data/8th_block --building-code 8TH_BLOCK --dry-run

Directory: nodes.csv + edges.csv (required), floors.csv (optional).
Legacy `import_nodes` (auto-topology) is untouched.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from navigation.importer import indoor_importer as ii
from navigation.importer.campus_importer import CampusImportError


class Command(BaseCommand):
    help = 'Imports an explicit indoor graph (nodes/edges/floors CSVs) for one building.'

    def add_arguments(self, parser):
        parser.add_argument('data_dir', help='Directory with nodes.csv + edges.csv')
        parser.add_argument('--building-code', required=True)
        parser.add_argument('--building-name', default='')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        base = Path(options['data_dir'])
        if not base.is_absolute():
            base = Path(__file__).resolve().parents[4] / base
        try:
            with transaction.atomic():
                summary = ii.import_indoor_directory(
                    base, options['building_code'], options['building_name'])
                if options['dry_run']:
                    transaction.set_rollback(True)
        except CampusImportError as e:
            raise CommandError('Indoor import failed:\n  • ' + '\n  • '.join(e.errors))
        except FileNotFoundError as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(
            ('Dry run OK, nothing written: ' if options['dry_run'] else 'Indoor import complete: ')
            + str(summary)))
