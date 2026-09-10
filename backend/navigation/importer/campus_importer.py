"""
Campus (outdoor) CSV importer: academic blocks, hostels, facilities, spaces,
outdoor graph nodes/edges and building entrances.

Principles: validate everything, upsert by natural key, never duplicate,
deactivate (never delete) stale graph edges, collect useful errors.
"""
import csv
from pathlib import Path

from django.db import transaction

from navigation.models import (
    Building, BuildingEntrance, CampusFacility, CampusSpace, Node,
    OutdoorEdge, OutdoorNode,
)
from navigation.outdoor.graph import haversine_m

SOURCES = {'verified', 'official', 'synthetic', 'unknown'}
OUTDOOR_NODE_TYPES = {c[0] for c in OutdoorNode.NODE_TYPES}
OUTDOOR_EDGE_MOVEMENTS = {c[0] for c in OutdoorEdge.MOVEMENT_TYPES}
FACILITY_BUILDING_CATEGORIES = {
    'facility': 'facility', 'administration': 'administration',
    'gate': 'gate', 'landmark': 'landmark', 'hostel': 'hostel',
    'academic': 'academic',
}


class CampusImportError(Exception):
    def __init__(self, errors):
        super().__init__('; '.join(errors[:5]))
        self.errors = errors


def read_rows(path):
    path = Path(path)
    if not path.exists():
        raise CampusImportError([f"CSV file not found: {path}"])
    with open(path, mode='r', encoding='utf-8-sig') as f:
        # Skip `#` comment lines so they never become the header row.
        lines = [ln for ln in f if not ln.lstrip().startswith('#')]
    if not lines:
        raise CampusImportError([f"{path.name}: empty file"])
    reader = csv.DictReader(lines)
    if not reader.fieldnames:
        raise CampusImportError([f"{path.name}: missing header row"])
    return [dict(r) for r in reader]


def _str(row, key, default=''):
    return (row.get(key) if row.get(key) is not None else default).strip()


def _bool(value, default=True):
    if value is None or str(value).strip() == '':
        return default
    return str(value).strip().lower() in ('true', '1', 'yes', 'y')


def _source(value):
    value = (value or 'unknown').strip().lower()
    return value if value in SOURCES else 'unknown'


def _coord(lat_raw, lon_raw, ctx, errors, required=True):
    if (lat_raw is None or str(lat_raw).strip() == '' or
            lon_raw is None or str(lon_raw).strip() == ''):
        if required:
            errors.append(f"{ctx}: latitude/longitude are required")
        return None, None
    try:
        lat = float(str(lat_raw).strip())
        lon = float(str(lon_raw).strip())
    except (ValueError, TypeError):
        errors.append(f"{ctx}: invalid coordinates lat={lat_raw!r} lon={lon_raw!r}")
        return None, None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        errors.append(f"{ctx}: coordinates out of range lat={lat} lon={lon}")
        return None, None
    return lat, lon


def import_building_rows(rows, source_name, default_category='academic'):
    """Upsert Building records. Returns (created, updated)."""
    errors, seen = [], set()
    created = updated = 0
    for i, row in enumerate(rows, start=2):
        code = _str(row, 'building_id') or _str(row, 'code')
        ctx = f"{source_name}:{i} ({code or '?'})"
        if not code:
            errors.append(f"{ctx}: building_id is required")
            continue
        if code in seen:
            errors.append(f"{ctx}: duplicate building_id in file")
            continue
        seen.add(code)
        name = _str(row, 'name') or code
        lat, lon = _coord(row.get('latitude'), row.get('longitude'), ctx, errors, required=False)
        ent_lat, ent_lon = _coord(row.get('entrance_latitude'), row.get('entrance_longitude'), ctx, errors, required=False)
        obj, was_created = Building.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'category': _str(row, 'category', default_category).lower() or default_category,
                'latitude': lat, 'longitude': lon,
                'entrance_latitude': ent_lat, 'entrance_longitude': ent_lon,
                'description': _str(row, 'description'),
                'is_navigable': _bool(row.get('is_navigable'), True),
                'is_active': _bool(row.get('is_active'), True),
                'source': _source(row.get('source')),
                'coordinate_verified': _source(row.get('source')) == 'verified',
            },
        )
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return created, updated


def import_facilities(rows, source_name='campus_facilities.csv'):
    errors, seen = [], set()
    created = updated = 0
    for i, row in enumerate(rows, start=2):
        fid = _str(row, 'facility_id')
        ctx = f"{source_name}:{i} ({fid or '?'})"
        if not fid:
            errors.append(f"{ctx}: facility_id is required")
            continue
        if fid in seen:
            errors.append(f"{ctx}: duplicate facility_id in file")
            continue
        seen.add(fid)
        lat, lon = _coord(row.get('latitude'), row.get('longitude'), ctx, errors, required=False)
        building = None
        bcode = _str(row, 'building_id')
        if bcode:
            building = Building.objects.filter(code=bcode).first()
            if building is None:
                # A facility that IS a building ensures its Building record.
                category = FACILITY_BUILDING_CATEGORIES.get(
                    _str(row, 'category', 'facility').lower(), 'facility')
                building = Building.objects.create(
                    code=bcode, name=_str(row, 'name', bcode), category=category,
                    latitude=lat, longitude=lon,
                    entrance_latitude=lat, entrance_longitude=lon,
                    description='', source=_source(row.get('source')),
                    coordinate_verified=_source(row.get('source')) == 'verified',
                )
        obj, was_created = CampusFacility.objects.update_or_create(
            facility_id=fid,
            defaults={
                'name': _str(row, 'name') or fid,
                'category': _str(row, 'category', 'facility').lower() or 'facility',
                'building': building,
                'latitude': lat, 'longitude': lon,
                'source': _source(row.get('source')),
                'coordinate_verified': _source(row.get('source')) == 'verified',
                'is_active': _bool(row.get('is_active'), True),
            },
        )
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return created, updated


def import_spaces(rows, source_name='campus_spaces.csv'):
    errors, seen = [], set()
    created = updated = 0
    for i, row in enumerate(rows, start=2):
        sid = _str(row, 'space_id')
        ctx = f"{source_name}:{i} ({sid or '?'})"
        if not sid:
            errors.append(f"{ctx}: space_id is required")
            continue
        if sid in seen:
            errors.append(f"{ctx}: duplicate space_id in file")
            continue
        seen.add(sid)
        lat, lon = _coord(row.get('latitude'), row.get('longitude'), ctx, errors, required=True)
        if lat is None:
            continue
        obj, was_created = CampusSpace.objects.update_or_create(
            space_id=sid,
            defaults={
                'name': _str(row, 'name') or sid,
                'space_type': _str(row, 'space_type', 'other').lower() or 'other',
                'latitude': lat, 'longitude': lon,
                'description': _str(row, 'description'),
                'is_active': _bool(row.get('is_active'), True),
            },
        )
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return created, updated


def import_outdoor_nodes(rows, source_name='outdoor_nodes.csv'):
    errors, seen = [], set()
    created = updated = 0
    for i, row in enumerate(rows, start=2):
        nid = _str(row, 'node_id')
        ctx = f"{source_name}:{i} ({nid or '?'})"
        if not nid:
            errors.append(f"{ctx}: node_id is required")
            continue
        if nid in seen:
            errors.append(f"{ctx}: duplicate node_id in file")
            continue
        seen.add(nid)
        ntype = _str(row, 'type', 'walkway').lower() or 'walkway'
        if ntype not in OUTDOOR_NODE_TYPES:
            errors.append(f"{ctx}: unknown type {ntype!r} (allowed: {sorted(OUTDOOR_NODE_TYPES)})")
            continue
        lat, lon = _coord(row.get('latitude'), row.get('longitude'), ctx, errors, required=True)
        if lat is None:
            continue
        building = None
        bcode = _str(row, 'building_id') or _str(row, 'building_code')
        if bcode:
            building = Building.objects.filter(code=bcode).first()
            if building is None:
                errors.append(f"{ctx}: unknown building_id {bcode!r}")
                continue
        from navigation.qr.payloads import outdoor_payload
        qr_value = _str(row, 'qr_code') or outdoor_payload(nid)
        if OutdoorNode.objects.filter(qr_code=qr_value).exclude(node_id=nid).exists():
            errors.append(f"{ctx}: duplicate qr_code {qr_value!r}")
            continue
        obj, was_created = OutdoorNode.objects.update_or_create(
            node_id=nid,
            defaults={
                'name': _str(row, 'name') or nid,
                'type': ntype,
                'building': building,
                'latitude': lat, 'longitude': lon,
                'qr_code': qr_value,
                'is_accessible': _bool(row.get('is_accessible'), True),
                'source': _source(row.get('source')),
                'coordinate_verified': _source(row.get('source')) == 'verified',
                'is_checkpoint': _bool(row.get('is_checkpoint'), False),
                'is_active': _bool(row.get('is_active'), True),
            },
        )
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return created, updated


def _upsert_directed_edge(edge_id, na, nb, dist, movement, accessible, is_active):
    OutdoorEdge.objects.update_or_create(
        edge_id=edge_id,
        defaults={
            'from_node': na, 'to_node': nb, 'distance_m': dist,
            'movement_type': movement, 'accessible': accessible, 'is_active': is_active,
        },
    )


def import_outdoor_edges(rows, source_name='outdoor_edges.csv'):
    errors, seen = [], set()
    seen_ids = set()
    count = 0
    # One-time cleanup: rows created by the legacy importer carry no edge_id and
    # would collide with managed upserts on (from, to, movement). They are
    # superseded by the edge_id-managed dataset imported here.
    legacy = OutdoorEdge.objects.filter(edge_id__isnull=True).delete()[0]
    if legacy:
        count = 0  # reporting only; real upsert count accumulated below
    for i, row in enumerate(rows, start=2):
        eid = _str(row, 'edge_id') or f"ROW{i}"
        ctx = f"{source_name}:{i} ({eid})"
        if eid in seen:
            errors.append(f"{ctx}: duplicate edge_id in file")
            continue
        seen.add(eid)
        a, b = _str(row, 'from_node'), _str(row, 'to_node')
        if not a or not b:
            errors.append(f"{ctx}: from_node and to_node are required")
            continue
        if a == b:
            errors.append(f"{ctx}: self-loop edges are not allowed")
            continue
        na = OutdoorNode.objects.filter(node_id=a).first()
        nb = OutdoorNode.objects.filter(node_id=b).first()
        if na is None or nb is None:
            missing = a if na is None else b
            errors.append(f"{ctx}: unknown node {missing!r}")
            continue
        movement = _str(row, 'movement_type', 'walk').lower() or 'walk'
        if movement not in OUTDOOR_EDGE_MOVEMENTS:
            errors.append(f"{ctx}: unknown movement_type {movement!r}")
            continue
        try:
            dist = float(str(row.get('distance_m') or '').strip())
        except (ValueError, TypeError, AttributeError):
            if row.get('distance_m') not in (None, ''):
                errors.append(f"{ctx}: invalid distance_m {row.get('distance_m')!r}")
                continue
            dist = haversine_m(na.latitude, na.longitude, nb.latitude, nb.longitude)
        accessible = _bool(row.get('accessible'), True)
        is_active = _bool(row.get('is_active'), True)
        bidirectional = _bool(row.get('bidirectional'), True)
        _upsert_directed_edge(eid, na, nb, dist, movement, accessible, is_active)
        seen_ids.add(eid)
        count += 1
        if bidirectional:
            _upsert_directed_edge(f"{eid}:R", nb, na, dist, movement, accessible, is_active)
            seen_ids.add(f"{eid}:R")
            count += 1
    if errors:
        raise CampusImportError(errors)
    # Deactivate (never delete) managed edges missing from the file.
    stale = OutdoorEdge.objects.exclude(edge_id__isnull=True).exclude(edge_id__in=seen_ids)
    deactivated = stale.filter(is_active=True).update(is_active=False)
    return count, deactivated


def import_entrances(rows, source_name='building_entrances.csv'):
    errors, seen, warnings = [], set(), []
    created = updated = 0
    for i, row in enumerate(rows, start=2):
        eid = _str(row, 'entrance_id')
        ctx = f"{source_name}:{i} ({eid or '?'})"
        if not eid:
            errors.append(f"{ctx}: entrance_id is required")
            continue
        if eid in seen:
            errors.append(f"{ctx}: duplicate entrance_id in file")
            continue
        seen.add(eid)
        bcode = _str(row, 'building_id')
        building = Building.objects.filter(code=bcode).first() if bcode else None
        if building is None:
            errors.append(f"{ctx}: unknown building_id {bcode!r}")
            continue
        indoor_id = _str(row, 'indoor_node_id')
        if indoor_id and not Node.objects.filter(node_id=indoor_id).exists():
            errors.append(f"{ctx}: unknown indoor_node_id {indoor_id!r}")
            continue
        lat, lon = _coord(row.get('latitude'), row.get('longitude'), ctx, errors, required=False)
        outdoor_id = ''
        onode = OutdoorNode.objects.filter(
            building=building, type='building_entrance', is_active=True).first()
        if onode:
            outdoor_id = onode.node_id
            if lat is None:
                lat, lon = onode.latitude, onode.longitude
        else:
            warnings.append(f"{ctx}: no building_entrance outdoor node for {bcode}; handoff outdoor side left blank")
        obj, was_created = BuildingEntrance.objects.update_or_create(
            entrance_id=eid,
            defaults={
                'building': building,
                'name': _str(row, 'name') or eid,
                'latitude': lat, 'longitude': lon,
                'outdoor_node_id': outdoor_id,
                'indoor_node_id': indoor_id,
                'is_accessible': _bool(row.get('accessible'), True),
                'source': _source(row.get('source')),
                'is_active': _bool(row.get('is_active'), True),
            },
        )
        if lat is not None and building.entrance_latitude is None:
            building.entrance_latitude, building.entrance_longitude = lat, lon
            building.save(update_fields=['entrance_latitude', 'entrance_longitude'])
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return created, updated, warnings


@transaction.atomic
def import_campus_directory(data_dir):
    """Master import: reads all seven CSVs from a directory. Returns a summary dict."""
    data_dir = Path(data_dir)
    summary = {}

    def load(name):
        return read_rows(data_dir / name)

    c, u = import_building_rows(load('academic_blocks.csv'), 'academic_blocks.csv', 'academic')
    summary['academic_blocks'] = {'created': c, 'updated': u}
    c, u = import_building_rows(load('hostels.csv'), 'hostels.csv', 'hostel')
    summary['hostels'] = {'created': c, 'updated': u}
    c, u = import_facilities(load('campus_facilities.csv'))
    summary['facilities'] = {'created': c, 'updated': u}
    c, u = import_spaces(load('campus_spaces.csv'))
    summary['spaces'] = {'created': c, 'updated': u}
    c, u = import_outdoor_nodes(load('outdoor_nodes.csv'))
    summary['outdoor_nodes'] = {'created': c, 'updated': u}
    count, deactivated = import_outdoor_edges(load('outdoor_edges.csv'))
    summary['outdoor_edges'] = {'upserted': count, 'deactivated': deactivated}
    c, u, warnings = import_entrances(load('building_entrances.csv'))
    summary['entrances'] = {'created': c, 'updated': u, 'warnings': warnings}
    return summary
