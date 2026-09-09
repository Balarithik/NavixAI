"""
QR Code Payload Validator for NavixAI.
Supports CAMPUSNAV:<node_id>, NAVIXAI:<node_id>, or raw <node_id>.
"""

from navigation.models import Node


class InvalidQRCodeError(Exception):
    pass


def validate_and_decode_qr(payload):
    """
    Decodes and validates a QR payload.
    Returns the corresponding active Node instance.
    """
    if not payload or not isinstance(payload, str):
        raise InvalidQRCodeError("Empty or invalid QR code payload provided.")

    payload = payload.strip()

    # Match by exact qr_code field in DB first
    node = Node.objects.filter(qr_code=payload, is_active=True).select_related('floor', 'building').first()
    if node:
        return node

    # Try matching by standard prefixes
    extracted_id = payload
    for prefix in ("NAVIXAI:", "CAMPUSNAV:"):
        if payload.upper().startswith(prefix):
            extracted_id = payload[len(prefix):].strip()
            break

    node = Node.objects.filter(node_id__iexact=extracted_id, is_active=True).select_related('floor', 'building').first()
    if node:
        return node

    raise InvalidQRCodeError(f"No active location found matching QR code '{payload}'.")
