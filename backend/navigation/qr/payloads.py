"""
Unified QR payload formats (backend-authoritative, documented contract).

Canonical (preferred for newly printed codes):
    CAMPUSNAV|OUTDOOR|<OUTDOOR_NODE_ID>
    CAMPUSNAV|INDOOR|<BUILDING_CODE>|<FLOOR_NUMBER>|<NODE_ID>

Legacy (still accepted — thousands of printed indoor codes use these):
    CAMPUSNAV:<node_id>   NAVIXAI:<node_id>   <raw node_id>

React must never hard-code payload↔location mappings; always POST /api/scan/.
"""


def outdoor_payload(node_id):
    return f"CAMPUSNAV|OUTDOOR|{(node_id or '').strip().upper()}"


def indoor_payload(building_code, floor_number, node_id):
    return (f"CAMPUSNAV|INDOOR|{(building_code or '').strip().upper()}|"
            f"{floor_number}|{(node_id or '').strip().upper()}")


def parse_payload(payload):
    """Returns a dict describing the payload, or None if unrecognised."""
    if not payload or not isinstance(payload, str):
        return None
    text = payload.strip()
    upper = text.upper()
    if upper.startswith('CAMPUSNAV|'):
        parts = text.split('|')
        kind = parts[1].upper() if len(parts) > 1 else ''
        if kind == 'OUTDOOR' and len(parts) == 3 and parts[2].strip():
            return {'location_type': 'outdoor', 'location_id': parts[2].strip()}
        if kind == 'INDOOR' and len(parts) == 5 and parts[4].strip():
            try:
                floor = int(parts[3])
            except (ValueError, TypeError):
                return None
            return {'location_type': 'indoor', 'building_code': parts[2].strip(),
                    'floor': floor, 'location_id': parts[4].strip()}
        return None
    # Legacy colon formats / raw ids resolve to indoor node ids.
    node_id = text
    for prefix in ('NAVIXAI:', 'CAMPUSNAV:'):
        if upper.startswith(prefix):
            node_id = text[len(prefix):].strip()
            break
    if not node_id:
        return None
    return {'location_type': 'indoor', 'location_id': node_id}
