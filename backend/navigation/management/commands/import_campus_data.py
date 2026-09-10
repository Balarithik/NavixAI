"""
Master campus-data import.

    python manage.py import_campus_data            # imports data/
    python manage.py import_campus_data data/      # explicit directory
    python manage.py import_campus_data --only outdoor_edges
    python manage.py import_campus_data --dry-run  # validate only

Expected files: academic_blocks.csv, hostels.csv, campus_facilities.csv,
campus_spaces.csv, outdoor_nodes.csv, outdoor_edges.csv, building_entrances.csv
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from navigation.importer import campus_importer as ci
from navigation.importer.campus_importer import CampusImportError

STEPS = (
    'academic_blocks', 'hostels', 'facilities', 'spaces',
    'outdoor_nodes', 'outdoor_edges', 'entrances',
)
FILES = {
    'academic_blocks': 'academic_blocks.csv',
    'hostels': 'hostels.csv',
    'facilities': 'campus_facilities.csv',
    'spaces': 'campus_spaces.csv',
    'outdoor_nodes': 'outdoor_nodes.csv',
    'outdoor_edges': 'outdoor_edges.csv',
    'entrances': 'building_entrances.csv',
}


def run_step(step, base):
    if step == 'academic_blocks':
        c, u = ci.import_building_rows(ci.read_rows(base / FILES[step]), 'academic_blocks.csv', 'academic')
        return {'created': c, 'updated': u}
    if step == 'hostels':
        c, u = ci.import_building_rows(ci.read_rows(base / FILES[step]), 'hostels.csv', 'hostel')
        return {'created': c, 'updated': u}
    if step == 'facilities':
        c, u = ci.import_facilities(ci.read_rows(base / FILES[step]))
        return {'created': c, 'updated': u}
    if step == 'spaces':
        c, u = ci.import_spaces(ci.read_rows(base / FILES[step]))
        return {'created': c, 'updated': u}
    if step == 'outdoor_nodes':
        c, u = ci.import_outdoor_nodes(ci.read_rows(base / FILES[step]))
        return {'created': c, 'updated': u}
    if step == 'outdoor_edges':
        count, deactivated = ci.import_outdoor_edges(ci.read_rows(base / FILES[step]))
        return {'upserted': count, 'deactivated': deactivated}
    if step == 'entrances':
        c, u, warnings = ci.import_entrances(ci.read_rows(base / FILES[step]))
        return {'created': c, 'updated': u, 'warnings': warnings}
    raise CommandError(f"Unknown step: {step}")


class Command(BaseCommand):
    help = 'Validates and imports all campus CSV datasets (idempotent upsert).'

    def add_arguments(self, parser):
        parser.add_argument('data_dir', nargs='?', default='data',
                            help='Directory containing the campus CSV files')
        parser.add_argument('--only', choices=STEPS, default=None,
                            help='Import a single dataset step')
        parser.add_argument('--dry-run', action='store_true',
                            help='Validate files without writing to the database')

    def handle(self, *args, **options):
        base = Path(options['data_dir'])
        if not base.is_absolute():
            base = Path(__file__).resolve().parents[4] / base
        steps = [options['only']] if options['only'] else list(STEPS)
        try:
            with transaction.atomic():
                summary = {step: run_step(step, base) for step in steps}
                if options['dry_run']:
                    # Roll back: validation only.
                    transaction.set_rollback(True)
        except CampusImportError as e:
            raise CommandError('Campus import failed:\n  • ' + '\n  • '.join(e.errors))
        for step, info in summary.items():
            self.stdout.write(f"  {step}: {info}")
            for w in info.get('warnings', []) if isinstance(info, dict) else []:
                self.stdout.write(self.style.WARNING(f"    warning: {w}"))
        msg = 'Dry run OK: all files valid, nothing written.' if options['dry_run'] \
            else 'Campus data import complete.'
        self.stdout.write(self.style.SUCCESS(msg))
