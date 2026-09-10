"""
Unified navigation service: decides outdoor / indoor / outdoor→indoor routing.

Destination model:
  {'type': 'building'|'room'|'outdoor', 'building_code': ..., 'floor': ..., 'indoor_node_id': ...}

Origin model:
  {'type': 'outdoor_node', 'node_id': ...}  (GPS snaps to nearest outdoor node)
  {'type': 'indoor_node', 'node_id': ...}   (QR / manual indoor position)
"""
import math

from navigation.models import Building, BuildingEntrance, CampusFacility, CampusSpace, Node, OutdoorNode
from navigation.outdoor.graph import haversine_m
from navigation.outdoor.route_engine import OutdoorRouteEngine
from navigation.routing.route_engine import RouteEngine


def nearest_outdoor_node(latitude, longitude):
    best, best_dist = None, None
    for n in OutdoorNode.objects.filter(is_active=True):
        d = haversine_m(latitude, longitude, n.latitude, n.longitude)
        if best_dist is None or d < best_dist:
            best, best_dist = n, d
    return best


def resolve_destination(raw):
    """Normalise a destination dict / search-result dict."""
    dtype = (raw.get('type') or '').lower()
    if dtype == 'room' or raw.get('indoor_node_id'):
        node_id = raw.get('indoor_node_id') or raw.get('id')
        node = Node.objects.filter(node_id__iexact=node_id, is_active=True).select_related('floor', 'building').first()
        if not node:
            raise ValueError(f"Indoor destination '{node_id}' not found")
        return {
            'kind': 'indoor', 'type': 'room', 'name': node.name,
            'building_code': node.building.code, 'building_name': node.building.name,
            'floor': node.floor.floor_number, 'indoor_node_id': node.node_id,
        }
    if dtype == 'building' or raw.get('building_code'):
        code = raw.get('building_code') or raw.get('id')
        b = Building.objects.filter(code__iexact=code, is_active=True).first()
        if not b:
            raise ValueError(f"Building '{code}' not found")
        return {
            'kind': 'outdoor', 'type': 'building', 'name': b.name,
            'building_code': b.code, 'building_name': b.name,
            'floor': None,
            'latitude': b.entrance_latitude or b.latitude,
            'longitude': b.entrance_longitude or b.longitude,
        }
    if dtype == 'facility':
        fac = CampusFacility.objects.filter(
            facility_id__iexact=raw.get('id', ''), is_active=True
        ).select_related('building').first()
        if not fac:
            raise ValueError(f"Facility '{raw.get('id')}' not found")
        if fac.building:
            return resolve_destination(
                {'type': 'building', 'id': fac.building.code, 'building_code': fac.building.code})
        if fac.latitude is None:
            raise ValueError(f"Facility '{fac.name}' has no mapped location")
        snap = nearest_outdoor_node(fac.latitude, fac.longitude)
        if not snap:
            raise ValueError('No outdoor navigation points available')
        return {
            'kind': 'outdoor', 'type': 'facility', 'name': fac.name,
            'building_code': None, 'building_name': None,
            'floor': None, 'outdoor_node_id': snap.node_id,
            'latitude': fac.latitude, 'longitude': fac.longitude,
        }
    if dtype == 'space':
        space = CampusSpace.objects.filter(
            space_id__iexact=raw.get('id', ''), is_active=True).first()
        if not space:
            raise ValueError(f"Campus space '{raw.get('id')}' not found")
        if space.latitude is None:
            raise ValueError(f"Campus space '{space.name}' has no mapped location")
        snap = nearest_outdoor_node(space.latitude, space.longitude)
        if not snap:
            raise ValueError('No outdoor navigation points available')
        return {
            'kind': 'outdoor', 'type': 'space', 'name': space.name,
            'building_code': None, 'building_name': None,
            'floor': None, 'outdoor_node_id': snap.node_id,
            'latitude': space.latitude, 'longitude': space.longitude,
        }
    if dtype == 'outdoor' or raw.get('node_id'):
        node_id = raw.get('node_id') or raw.get('id')
        n = OutdoorNode.objects.filter(node_id__iexact=node_id, is_active=True).select_related('building').first()
        if not n:
            raise ValueError(f"Outdoor destination '{node_id}' not found")
        return {
            'kind': 'outdoor', 'type': 'outdoor', 'name': n.name,
            'building_code': n.building.code if n.building else None,
            'building_name': n.building.name if n.building else None,
            'floor': None, 'outdoor_node_id': n.node_id,
            'latitude': n.latitude, 'longitude': n.longitude,
        }
    raise ValueError('Unrecognised destination')


def resolve_origin(raw):
    otype = (raw.get('type') or '').lower()
    if otype in ('indoor_node', 'indoor') or raw.get('indoor_node_id'):
        node_id = raw.get('indoor_node_id') or raw.get('node_id')
        node = Node.objects.filter(node_id__iexact=node_id, is_active=True).select_related('floor', 'building').first()
        if not node:
            raise ValueError(f"Indoor origin '{node_id}' not found")
        return {'kind': 'indoor', 'indoor_node_id': node.node_id,
                'building_code': node.building.code, 'name': node.name}
    if otype in ('outdoor_node', 'outdoor') or raw.get('outdoor_node_id'):
        node_id = raw.get('outdoor_node_id') or raw.get('node_id')
        n = OutdoorNode.objects.filter(node_id__iexact=node_id, is_active=True).first()
        if not n:
            raise ValueError(f"Outdoor origin '{node_id}' not found")
        return {'kind': 'outdoor', 'outdoor_node_id': n.node_id, 'name': n.name}
    if raw.get('latitude') is not None and raw.get('longitude') is not None:
        nearest = nearest_outdoor_node(float(raw['latitude']), float(raw['longitude']))
        if not nearest:
            raise ValueError('No outdoor navigation points available')
        return {'kind': 'outdoor', 'outdoor_node_id': nearest.node_id,
                'name': nearest.name, 'snapped': True}
    raise ValueError('Unrecognised origin')


def building_entrance_for(building_code):
    return BuildingEntrance.objects.filter(
        building__code__iexact=building_code, is_active=True
    ).select_related('building').first()


def _indoor_leg(from_node_id, to_node_id, mode):
    """One indoor Dijkstra leg (building/floor context is derived from its path)."""
    return RouteEngine().calculate_route(from_node_id, to_node_id, mode=mode)


def _indoor_summary(node_id):
    n = Node.objects.filter(node_id__iexact=node_id, is_active=True).select_related('floor', 'building').first()
    if not n:
        return None
    return {'building_code': n.building.code, 'building_name': n.building.name,
            'floor': n.floor.floor_number, 'floor_name': n.floor.name}


def _segment_title(seg):
    if seg['type'] == 'outdoor':
        return 'Outdoor campus'
    # Title by destination floor (where the leg ends); segment covers one floor
    # unless it is a vertical transition, in which case show the range.
    to = seg.get('to') or {}
    if to.get('building_name'):
        seg['building_code'] = to.get('building_code')
        seg['floor'] = to.get('floor')
        from_floor = (seg.get('from') or {}).get('floor')
        if from_floor is not None and from_floor != to.get('floor'):
            return f"{to['building_name']} • Floors {from_floor} → {to['floor']}"
        return f"{to['building_name']} • {to.get('floor_name', '')}".strip()
    return 'Indoors'


def _require_entrance(building_code, side):
    entrance = building_entrance_for(building_code)
    if not entrance or not entrance.outdoor_node_id or not entrance.indoor_node_id:
        raise ValueError(f"No complete entrance bridge for building '{building_code}' ({side})")
    return entrance


def calculate_unified_route(origin_raw, destination_raw, mode='any'):
    origin = resolve_origin(origin_raw)
    dest = resolve_destination(destination_raw)
    segments = []

    def fail(payload, route_type):
        payload = dict(payload)
        payload['mode'] = route_type  # backward-compat alias
        payload['routeType'] = route_type
        return payload

    if dest['kind'] == 'outdoor':
        target_outdoor = dest.get('outdoor_node_id')
        if target_outdoor and not OutdoorNode.objects.filter(
                node_id__iexact=target_outdoor, is_active=True).exists():
            target_outdoor = None
        if not target_outdoor:
            entrance = building_entrance_for(dest['building_code']) if dest.get('building_code') else None
            target_outdoor = (entrance.outdoor_node_id if entrance and entrance.outdoor_node_id
                              else _entrance_outdoor_node(dest.get('building_code')))
        if not target_outdoor and dest.get('latitude') is not None:
            # Standalone POI (facility/space): snap to the nearest graph node.
            snap = nearest_outdoor_node(dest['latitude'], dest['longitude'])
            target_outdoor = snap.node_id if snap else None
        if not target_outdoor:
            raise ValueError(f"No walkable route target for '{dest.get('name')}'")
        if origin['kind'] == 'indoor':
            # Indoor → outdoor: walk out through the origin building's entrance first.
            entrance = _require_entrance(origin['building_code'], 'origin')
            first = _indoor_leg(origin['indoor_node_id'], entrance.indoor_node_id, mode)
            if not first.get('success'):
                return fail({**first, 'destination': dest, 'segments': segments}, 'indoor_to_outdoor')
            segments.append({**first, 'type': 'indoor'})
            origin_outdoor = entrance.outdoor_node_id
            route_type = 'indoor_to_outdoor'
        else:
            origin_outdoor = origin['outdoor_node_id']
            route_type = 'outdoor'
        seg = OutdoorRouteEngine().calculate_route(origin_outdoor, target_outdoor)
        if not seg.get('success'):
            return fail({**seg, 'destination': dest, 'segments': segments}, route_type)
        segments.append({**seg, 'type': 'outdoor'})
    else:
        # ---- indoor destination ----
        entrance = _require_entrance(dest['building_code'], 'destination') \
            if origin.get('building_code') != dest['building_code'] or origin['kind'] == 'outdoor' \
            else building_entrance_for(dest['building_code'])
        if origin['kind'] == 'outdoor':
            seg = OutdoorRouteEngine().calculate_route(origin['outdoor_node_id'], entrance.outdoor_node_id)
            if not seg.get('success'):
                return fail({**seg, 'destination': dest, 'segments': segments}, 'outdoor_to_indoor')
            segments.append({**seg, 'type': 'outdoor'})
            indoor_origin = entrance.indoor_node_id
            route_type = 'outdoor_to_indoor'
        elif origin.get('building_code') != dest['building_code']:
            # ---- multi-building: indoor → outdoor → indoor ----
            origin_entrance = _require_entrance(origin['building_code'], 'origin')
            first = _indoor_leg(origin['indoor_node_id'], origin_entrance.indoor_node_id, mode)
            if not first.get('success'):
                return fail({**first, 'destination': dest, 'segments': segments}, 'multi_building')
            segments.append({**first, 'type': 'indoor'})
            mid = OutdoorRouteEngine().calculate_route(
                origin_entrance.outdoor_node_id, entrance.outdoor_node_id)
            if not mid.get('success'):
                return fail({**mid, 'destination': dest, 'segments': segments}, 'multi_building')
            segments.append({**mid, 'type': 'outdoor'})
            indoor_origin = entrance.indoor_node_id
            route_type = 'multi_building'
        else:
            indoor_origin = origin['indoor_node_id']
            route_type = 'indoor'

        if indoor_origin:
            indoor = _indoor_leg(indoor_origin, dest['indoor_node_id'], mode=mode)
            if not indoor.get('success'):
                return fail({**indoor, 'destination': dest, 'segments': segments}, route_type)
            segments.append({**indoor, 'type': 'indoor'})

    for seg in segments:
        seg['title'] = _segment_title(seg)

    total_dist = round(sum(s.get('distanceMetres', 0) for s in segments), 1)
    total_mins = max(1, math.ceil(sum(s.get('durationMinutes', 0) for s in segments)))
    instructions, checkpoints = [], []
    for idx, s in enumerate(segments):
        if idx > 0:
            prev, cur = segments[idx - 1], s
            if prev['type'] == 'indoor' and cur['type'] == 'outdoor':
                bname = (prev.get('from') or {}).get('building_name') or \
                    (_indoor_summary(prev['path'][0]['node_id']) or {}).get('building_name', 'the building')
                instructions.append(f"Exit {bname} onto the campus walkway.")
            elif prev['type'] == 'outdoor' and cur['type'] == 'indoor':
                bname = (cur.get('to') or {}).get('building_name') or \
                    (_indoor_summary(cur['path'][-1]['node_id']) or {}).get('building_name', 'the building')
                instructions.append(f"Enter {bname} and continue indoors.")
        prefix = 'Outdoors: ' if s['type'] == 'outdoor' else ''
        for step in s.get('instructions', []):
            if step.startswith(('Start at', 'Arrive at')) or not prefix:
                instructions.append(step)
            elif step:
                instructions.append(prefix + step[0:1].lower() + step[1:])
        checkpoints.extend([{**c, 'segment': s['type'], 'segment_index': idx,
                             'segment_title': s.get('title', s['type'])}
                            for c in s.get('checkpoints', [])])

    if route_type in ('unknown',):
        route_type = segments[0]['type'] if segments else 'unknown'
    return {
        'mode': route_type,  # backward-compat alias
        'routeType': route_type,
        'destination': dest,
        'origin': origin,
        'segments': segments,
        'totalDistanceMetres': total_dist,
        'totalDurationMinutes': total_mins,
        'instructions': instructions,
        'checkpoints': checkpoints,
    }


def _entrance_outdoor_node(building_code):
    if not building_code:
        return None
    n = OutdoorNode.objects.filter(
        building__code__iexact=building_code, type='building_entrance', is_active=True
    ).first()
    return n.node_id if n else None
