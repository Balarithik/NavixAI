"""
Explicit indoor graph importer (per-building directories).

    data/8th_block/nodes.csv
    data/8th_block/edges.csv
    data/8th_block/floors.csv   (optional)

Unlike the legacy auto-topology importer, nodes AND edges are explicit data:
no proximity guessing, no hard-coded room ids. Vertical lift/stairs links are
ordinary edge rows across floors. The legacy `import_nodes` flow is untouched.

nodes.csv: node_id,building_id,floor,block,name,type,x,y,qr_code[,is_active]
edges.csv: edge_id,from_node,to_node,distance_m,movement_type,accessible,bidirectional,is_active
floors.csv: floor_number,name[,map_asset,map_width,map_height]
"""
import math

from django.conf import settings
from django.db import transaction

from navigation.models import Building, Edge, Floor, Node, QRCode
from .campus_importer import CampusImportError, read_rows

INDOOR_MOVEMENTS = {'walk', 'stairs', 'lift'}
CHECKPOINT_TYPES = {'entrance', 'junction', 'lift', 'stair'}


def _s(row, key, default=''):
    v = row.get(key)
    return (v if v is not None else default).strip() if isinstance(v, str) else (str(v).strip() if v is not None else default)


def _b(value, default=True):
    if value is None or str(value).strip() == '':
        return default
    return str(value).strip().lower() in ('true', '1', 'yes', 'y')


def _euclidean(a, b, scale):
    return round(math.hypot(b.x - a.x, b.y - a.y) * scale, 2)


def import_floors(building, rows, source_name='floors.csv'):
    errors = []
    floors = {}
    for i, row in enumerate(rows, start=2):
        try:
            fn = int(str(row.get('floor_number', '')).strip())
        except (ValueError, TypeError, AttributeError):
            errors.append(f"{source_name}:{i}: invalid floor_number {row.get('floor_number')!r}")
            continue
        defaults = {'name': _s(row, 'name', f'Floor {fn}')}
        if _s(row, 'map_asset'):
            defaults['map_asset'] = _s(row, 'map_asset')
        for key in ('map_width', 'map_height'):
            if _s(row, key):
                try:
                    defaults[key] = float(_s(row, key))
                except ValueError:
                    errors.append(f"{source_name}:{i}: invalid {key} {_s(row, key)!r}")
        floor, _ = Floor.objects.update_or_create(
            building=building, floor_number=fn, defaults=defaults)
        floors[fn] = floor
    if errors:
        raise CampusImportError(errors)
    return floors


def import_indoor_nodes(building, rows, source_name='nodes.csv'):
    from navigation.models import Node as NodeModel
    allowed = {c[0] for c in NodeModel.NODE_TYPES}
    errors, seen_ids, seen_qr = [], set(), set()
    created = updated = 0
    node_map = {}
    for i, row in enumerate(rows, start=2):
        nid = _s(row, 'node_id')
        ctx = f"{source_name}:{i} ({nid or '?'})"
        if not nid:
            errors.append(f"{ctx}: node_id is required")
            continue
        if nid in seen_ids:
            errors.append(f"{ctx}: duplicate node_id in file")
            continue
        seen_ids.add(nid)
        bcol = _s(row, 'building_id')
        if bcol and bcol.upper() != building.code.upper():
            errors.append(f"{ctx}: building_id {bcol!r} does not match {building.code}")
            continue
        try:
            fn = int(str(row.get('floor', '')).strip())
        except (ValueError, TypeError, AttributeError):
            errors.append(f"{ctx}: invalid floor {row.get('floor')!r}")
            continue
        ntype = _s(row, 'type', 'room').lower() or 'room'
        if ntype not in allowed:
            errors.append(f"{ctx}: unknown type {ntype!r}")
            continue
        try:
            x, y = float(row['x']), float(row['y'])
        except (ValueError, TypeError, KeyError):
            errors.append(f"{ctx}: invalid coordinates x={row.get('x')!r} y={row.get('y')!r}")
            continue
        qr = _s(row, 'qr_code') or f"CAMPUSNAV|INDOOR|{building.code}|{fn}|{nid}"
        if qr in seen_qr:
            errors.append(f"{ctx}: duplicate qr_code in file")
            continue
        seen_qr.add(qr)
        if Node.objects.filter(qr_code=qr).exclude(node_id=nid).exists():
            errors.append(f"{ctx}: qr_code already used by another node")
            continue
        floor, _ = Floor.objects.get_or_create(
            building=building, floor_number=fn, defaults={'name': f'Floor {fn}'})
        node, was_created = Node.objects.update_or_create(
            node_id=nid,
            defaults={
                'building': building,
                'block': _s(row, 'block', '1'),
                'name': _s(row, 'name') or nid,
                'type': ntype,
                'floor': floor,
                'x': x, 'y': y,
                'qr_code': qr,
                'is_checkpoint': ntype in CHECKPOINT_TYPES,
                'is_active': _b(row.get('is_active'), True),
            },
        )
        QRCode.objects.update_or_create(node=node, defaults={'payload': qr})
        node_map[nid] = node
        created, updated = (created + 1, updated) if was_created else (created, updated + 1)
    if errors:
        raise CampusImportError(errors)
    return node_map, created, updated


def import_indoor_edges(building, node_map, rows, source_name='edges.csv'):
    scale = getattr(settings, 'COORDINATE_SCALE_METRES', 1.0)
    penalty = getattr(settings, 'VERTICAL_FLOOR_PENALTY_METRES', 15.0)
    errors, seen = [], set()
    seen_ids = set()
    count = 0

    def upsert(edge_id, na, nb, dist, movement, accessible, is_active):
        Edge.objects.update_or_create(
            edge_id=edge_id,
            defaults={'from_node': na, 'to_node': nb, 'distance': dist,
                      'movement_type': movement, 'accessible': accessible,
                      'is_active': is_active},
        )

    for i, row in enumerate(rows, start=2):
        eid = _s(row, 'edge_id')
        ctx = f"{source_name}:{i} ({eid or '?'})"
        if not eid:
            errors.append(f"{ctx}: edge_id is required")
            continue
        if eid in seen:
            errors.append(f"{ctx}: duplicate edge_id in file")
            continue
        seen.add(eid)
        a, b = _s(row, 'from_node'), _s(row, 'to_node')
        if not a or not b:
            errors.append(f"{ctx}: from_node and to_node are required")
            continue
        if a == b:
            errors.append(f"{ctx}: self-loop edges are not allowed")
            continue
        na, nb = node_map.get(a), node_map.get(b)
        if na is None or nb is None:
            errors.append(f"{ctx}: unknown node {(a if na is None else b)!r}")
            continue
        movement = _s(row, 'movement_type', 'walk').lower() or 'walk'
        if movement not in INDOOR_MOVEMENTS:
            errors.append(f"{ctx}: unknown movement_type {movement!r}")
            continue
        dist_raw = _s(row, 'distance_m')
        if dist_raw:
            try:
                dist = float(dist_raw)
            except ValueError:
                errors.append(f"{ctx}: invalid distance_m {dist_raw!r}")
                continue
        elif na.floor_id == nb.floor_id:
            dist = _euclidean(na, nb, scale)
        else:
            dist = penalty
        accessible = _b(row.get('accessible'), movement != 'stairs')
        is_active = _b(row.get('is_active'), True)
        upsert(eid, na, nb, dist, movement, accessible, is_active)
        seen_ids.add(eid)
        count += 1
        if _b(row.get('bidirectional'), True):
            upsert(f"{eid}:R", nb, na, dist, movement, accessible, is_active)
            seen_ids.add(f"{eid}:R")
            count += 1
    if errors:
        raise CampusImportError(errors)
    # Retire managed edges of this building that vanished from the file.
    stale = Edge.objects.filter(
        edge_id__isnull=False,
        from_node__building=building,
    ).exclude(edge_id__in=seen_ids)
    deactivated = stale.filter(is_active=True).update(is_active=False)
    return count, deactivated


@transaction.atomic
def import_indoor_directory(data_dir, building_code, building_name=''):
    """Full per-building import. Returns a summary dict."""
    from pathlib import Path
    data_dir = Path(data_dir)
    building, _ = Building.objects.get_or_create(
        code=building_code,
        defaults={'name': building_name or building_code, 'category': 'academic'})
    summary = {'building': building.code}
    floors_path = data_dir / 'floors.csv'
    if floors_path.exists():
        floors = import_floors(building, read_rows(floors_path))
        summary['floors'] = len(floors)
    node_map, created, updated = import_indoor_nodes(
        building, read_rows(data_dir / 'nodes.csv'))
    # Drop legacy auto-generated (edge_id NULL) edges for this building: superseded.
    Edge.objects.filter(edge_id__isnull=True, from_node__building=building).delete()
    count, deactivated = import_indoor_edges(
        building, node_map, read_rows(data_dir / 'edges.csv'))
    summary.update({'nodes_created': created, 'nodes_updated': updated,
                    'edges_upserted': count, 'edges_deactivated': deactivated})
    return summary
