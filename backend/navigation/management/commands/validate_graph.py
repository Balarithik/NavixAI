"""
Validates navigation graph integrity (indoor + outdoor + bridges).

    python manage.py validate_graph
    python manage.py validate_graph --building 8TH_BLOCK

Checks: isolated nodes (no edges), edges touching inactive nodes,
entrances missing indoor/outdoor links, buildings without floors.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from navigation.models import (
    Building, BuildingEntrance, Edge, Node, OutdoorEdge, OutdoorNode,
)


class Command(BaseCommand):
    help = 'Validates indoor/outdoor graph integrity.'

    def add_arguments(self, parser):
        parser.add_argument('--building', default=None)

    def handle(self, *args, **options):
        issues = []
        code = options['building']

        nodes = Node.objects.filter(is_active=True)
        if code:
            nodes = nodes.filter(building__code__iexact=code)
        connected = set(Edge.objects.filter(is_active=True).values_list('from_node_id', flat=True))
        connected |= set(Edge.objects.filter(is_active=True).values_list('to_node_id', flat=True))
        for n in nodes.only('node_id', 'name').iterator():
            if n.id not in connected:
                issues.append(f"isolated indoor node: {n.node_id} ({n.name})")

        dead = Edge.objects.filter(is_active=True).filter(
            Q(from_node__is_active=False) | Q(to_node__is_active=False)).count()
        if dead:
            issues.append(f"{dead} active edge(s) touch inactive nodes")

        onodes = OutdoorNode.objects.filter(is_active=True)
        oconnected = set(OutdoorEdge.objects.filter(is_active=True).values_list('from_node_id', flat=True))
        oconnected |= set(OutdoorEdge.objects.filter(is_active=True).values_list('to_node_id', flat=True))
        for n in onodes.only('node_id', 'name').iterator():
            if n.id not in oconnected:
                issues.append(f"isolated outdoor node: {n.node_id} ({n.name})")

        entrances = BuildingEntrance.objects.filter(is_active=True).select_related('building')
        if code:
            entrances = entrances.filter(building__code__iexact=code)
        for e in entrances.iterator():
            if not e.outdoor_node_id:
                issues.append(f"entrance {e.entrance_id}: missing outdoor link")
            if not e.indoor_node_id:
                issues.append(f"entrance {e.entrance_id}: missing indoor link (outdoor-only building)")

        buildings = Building.objects.filter(is_active=True)
        if code:
            buildings = buildings.filter(code__iexact=code)
        buildings = buildings.annotate(floor_count=Count('floors'))
        for b in buildings.iterator():
            if b.floor_count == 0 and b.is_navigable and b.category in ('academic', 'hostel'):
                issues.append(f"building {b.code}: navigable but has no floors")

        if issues:
            self.stdout.write(self.style.WARNING(f"{len(issues)} issue(s):"))
            for i in issues:
                self.stdout.write(f"  • {i}")
        else:
            self.stdout.write(self.style.SUCCESS('Graph validation passed: no issues found.'))
