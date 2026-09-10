"""
Legacy campus import (deprecated, kept for backward compatibility).

The campus data now lives in split CSV files imported by `import_campus_data`.
This command delegates to the same importer so old scripts keep working.
"""
from django.core.management.base import BaseCommand

from .import_campus_data import STEPS, run_step
from pathlib import Path


class Command(BaseCommand):
    help = 'Deprecated: use `import_campus_data`. Imports campus datasets from data/.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'import_campus is deprecated; use `python manage.py import_campus_data`.'))
        base = Path(__file__).resolve().parents[4] / 'data'
        summary = {step: run_step(step, base) for step in STEPS}
        for step, info in summary.items():
            self.stdout.write(f"  {step}: {info}")
        self.stdout.write(self.style.SUCCESS('Campus import complete.'))
