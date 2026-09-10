"""
Unified campus search: buildings, outdoor places, indoor rooms.
All results resolve to a destination model the navigation service understands.
"""
from django.db.models import Q

from navigation.models import Building, CampusFacility, CampusSpace, Node, OutdoorNode


def search_campus(query, limit=12):
    query = (query or '').strip()
    if not query:
        return []
    results = []

    for b in Building.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query),
        is_active=True,
    ).order_by('name')[:limit]:
        results.append({
            'type': 'building',
            'id': b.code,
            'name': b.name,
            'subtitle': b.get_category_display(),
            'building_code': b.code,
            'building_name': b.name,
            'floor': None,
            'latitude': b.latitude,
            'longitude': b.longitude,
        })

    for n in OutdoorNode.objects.filter(
        Q(name__icontains=query) | Q(node_id__icontains=query),
        is_active=True,
    ).select_related('building').order_by('name')[:limit]:
        results.append({
            'type': 'outdoor',
            'id': n.node_id,
            'name': n.name,
            'subtitle': n.get_type_display(),
            'building_code': n.building.code if n.building else None,
            'building_name': n.building.name if n.building else None,
            'floor': None,
            'latitude': n.latitude,
            'longitude': n.longitude,
        })

    for f in CampusFacility.objects.filter(
        Q(name__icontains=query) | Q(facility_id__icontains=query),
        is_active=True,
    ).select_related('building').order_by('name')[:limit]:
        results.append({
            'type': 'facility',
            'id': f.facility_id,
            'name': f.name,
            'subtitle': (f.building.name if f.building else f.category or 'Facility'),
            'building_code': f.building.code if f.building else None,
            'building_name': f.building.name if f.building else None,
            'floor': None,
            'latitude': f.latitude,
            'longitude': f.longitude,
        })

    for s in CampusSpace.objects.filter(
        Q(name__icontains=query) | Q(space_id__icontains=query),
        is_active=True,
    ).order_by('name')[:limit]:
        results.append({
            'type': 'space',
            'id': s.space_id,
            'name': s.name,
            'subtitle': (s.space_type or 'Campus space').replace('_', ' '),
            'building_code': None,
            'building_name': None,
            'floor': None,
            'latitude': s.latitude,
            'longitude': s.longitude,
        })

    for node in Node.objects.filter(
        Q(name__icontains=query) | Q(node_id__icontains=query),
        is_active=True,
    ).select_related('floor', 'building').order_by('building__code', 'floor__floor_number', 'name')[:limit]:
        results.append({
            'type': 'room',
            'id': node.node_id,
            'name': node.name,
            'subtitle': f"{node.building.name} · Floor {node.floor.floor_number}",
            'building_code': node.building.code,
            'building_name': node.building.name,
            'floor': node.floor.floor_number,
            'latitude': None,
            'longitude': None,
            'indoor_node_id': node.node_id,
        })

    return results[:limit]
