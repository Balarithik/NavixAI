from django.core.management.base import BaseCommand
from navigation.models import Node
from navigation.qr.generator import QRCodeGenerator


class Command(BaseCommand):
    help = 'Generates physical QR code PNG images for all active nodes in the database.'

    def handle(self, *args, **options):
        nodes = Node.objects.filter(is_active=True)
        generator = QRCodeGenerator()
        count = 0

        self.stdout.write(f"Generating QR code images for {nodes.count()} nodes...")
        for node in nodes:
            filepath = generator.generate_and_save_for_node(node)
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully generated {count} QR code images in '{generator.output_dir}'."
        ))
