"""
QR Code Payload Validator for NavixAI (unified outdoor + indoor).

Canonical: CAMPUSNAV|OUTDOOR|<node_id>, CAMPUSNAV|INDOOR|<bldg>|<floor>|<node_id>.
Legacy indoor: CAMPUSNAV:<node_id>, NAVIXAI:<node_id>, raw <node_id>.
"""

from navigation.models import Node, OutdoorNode
from .payloads import parse_payload


class InvalidQRCodeError(Exception):
    pass


def validate_location(payload):
    """
    Validates any CampusNav QR payload.
    Returns {'location_type': 'outdoor'|'indoor', 'outdoor_node'|'node': instance}.
    """
    if not payload or not isinstance(payload, str):
        raise InvalidQRCodeError("This QR code is not a valid CampusNav location.")
    text = payload.strip()

    # Exact outdoor payload match first (covers canonical + explicit CSV values).
    outdoor = OutdoorNode.objects.filter(qr_code=text, is_active=True).select_related('building').first()
    if outdoor:
        return {'location_type': 'outdoor', 'outdoor_node': outdoor}

    # Exact indoor payload match (covers legacy CAMPUSNAV:/NAVIXAI: codes).
    node = Node.objects.filter(qr_code=text, is_active=True).select_related('floor', 'building').first()
    if node:
        return {'location_type': 'indoor', 'node': node}

    parsed = parse_payload(text)
    if not parsed:
        raise InvalidQRCodeError("This QR code is not a valid CampusNav location.")

    if parsed['location_type'] == 'outdoor':
        outdoor = OutdoorNode.objects.filter(
            node_id__iexact=parsed['location_id'], is_active=True).select_related('building').first()
        if outdoor:
            return {'location_type': 'outdoor', 'outdoor_node': outdoor}
        raise InvalidQRCodeError("CampusNav could not find this location.")

    node = Node.objects.filter(
        node_id__iexact=parsed['location_id'], is_active=True).select_related('floor', 'building').first()
    if node:
        return {'location_type': 'indoor', 'node': node}
    raise InvalidQRCodeError("CampusNav could not find this location.")


def validate_and_decode_qr(payload):
    """
    Legacy indoor-only entry point (kept for existing callers/tests).
    Returns the corresponding active indoor Node instance.
    """
    result = validate_location(payload)
    if result['location_type'] != 'indoor':
        raise InvalidQRCodeError("This QR code is not an indoor location.")
    return result['node']
