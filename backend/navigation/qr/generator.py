"""
QR Code Generator for NavixAI using Python's qrcode library.
"""

import io
from pathlib import Path
import qrcode
from django.conf import settings
from navigation.models import Node, QRCode


class QRCodeGenerator:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir or getattr(settings, 'QR_STORAGE_DIR', settings.BASE_DIR.parent / 'qr_codes'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_image_stream(self, payload):
        """Generates QR code image as an in-memory PNG BytesIO buffer."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def generate_and_save_for_node(self, node):
        """Generates and saves a PNG file for a specific node."""
        filename = f"{node.node_id}.png"
        filepath = self.output_dir / filename

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        payload = node.qr_code or f"NAVIXAI:{node.node_id}"
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF")
        img.save(str(filepath), format='PNG')

        # Update or create QRCode record
        QRCode.objects.update_or_create(
            node=node,
            defaults={
                'payload': payload,
                'image_path': f"qr_codes/{filename}"
            }
        )
        return filepath
