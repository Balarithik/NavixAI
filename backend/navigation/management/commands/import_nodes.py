from django.core.management.base import BaseCommand, CommandError
from navigation.importer.csv_parser import BuildingCSVImporter
from navigation.importer.validator import CSVValidationError


class Command(BaseCommand):
    help = 'Imports indoor building nodes and builds navigation edges from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the building nodes CSV file')
        parser.add_argument('--building-code', type=str, default='MAIN', help='Unique code for the building')
        parser.add_argument('--building-name', type=str, default='Engineering & Tech Complex', help='Name of the building')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        building_code = options['building_code']
        building_name = options['building_name']

        self.stdout.write(self.style.NOTICE(f"Importing nodes from {csv_path} for {building_name} ({building_code})..."))

        try:
            importer = BuildingCSVImporter(
                file_path=csv_path,
                building_code=building_code,
                building_name=building_name
            )
            result = importer.import_data()

            self.stdout.write(self.style.SUCCESS(
                f"Successfully imported building '{result['building']}':\n"
                f" - Floors: {result['floors_count']}\n"
                f" - Nodes created: {result['nodes_created']}\n"
                f" - Nodes updated: {result['nodes_updated']}\n"
                f" - Total Nodes: {result['total_nodes']}\n"
                f" - Directed/Bidirectional Edges generated: {result['edges_count']}"
            ))

        except FileNotFoundError as e:
            raise CommandError(str(e))
        except CSVValidationError as e:
            self.stderr.write(self.style.ERROR(f"Validation failed with {len(e.errors)} errors:"))
            for err in e.errors:
                self.stderr.write(self.style.ERROR(f"  • {err}"))
            raise CommandError("CSV import aborted due to validation errors.")
        except Exception as e:
            raise CommandError(f"Unexpected error during import: {e}")
