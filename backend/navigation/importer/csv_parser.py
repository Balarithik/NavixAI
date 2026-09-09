"""
CSV Parser and Database Ingestion Service for NavixAI.
"""

import csv
import math
from pathlib import Path
from django.db import transaction
from django.conf import settings
from navigation.models import Building, Floor, Node, Edge, QRCode
from .validator import validate_csv_rows, CSVValidationError


def calculate_euclidean_distance(node_a, node_b, scale=1.0):
    """Calculates scaled Euclidean distance in metres."""
    dx = node_b.x - node_a.x
    dy = node_b.y - node_a.y
    return round(math.sqrt(dx * dx + dy * dy) * scale, 2)


class BuildingCSVImporter:
    def __init__(self, file_path, building_code="MAIN", building_name="Engineering & Tech Complex"):
        self.file_path = Path(file_path)
        self.building_code = building_code
        self.building_name = building_name
        self.scale = getattr(settings, 'COORDINATE_SCALE_METRES', 1.0)
        self.floor_penalty = getattr(settings, 'VERTICAL_FLOOR_PENALTY_METRES', 15.0)

    def parse_and_validate(self):
        """Reads CSV and validates headers and rows."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")

        with open(self.file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)

        clean_rows, errors = validate_csv_rows(raw_rows)
        if errors:
            raise CSVValidationError(errors)

        return clean_rows

    @transaction.atomic
    def import_data(self):
        """
        Imports validated rows into MySQL/SQLite database.
        Idempotent: updates existing records and creates missing ones.
        Generates indoor topological edges and vertical transitions.
        """
        clean_rows = self.parse_and_validate()

        # 1. Ensure Building exists
        building, _ = Building.objects.get_or_create(
            code=self.building_code,
            defaults={'name': self.building_name, 'description': 'Main Campus Navigation Complex'}
        )

        # 2. Ensure Floors exist
        floor_numbers = {row['floor'] for row in clean_rows}
        floor_map = {}
        for fn in floor_numbers:
            floor, _ = Floor.objects.get_or_create(
                building=building,
                floor_number=fn,
                defaults={'name': f"Floor {fn}", 'map_width': 100.0, 'map_height': 100.0}
            )
            floor_map[fn] = floor

        # 3. Create or update Nodes
        node_records = {}
        created_nodes = 0
        updated_nodes = 0

        # Designate key nodes as checkpoints (entrances, junctions, lifts, stairs)
        checkpoint_types = {'entrance', 'junction', 'lift', 'stair'}

        for row in clean_rows:
            is_checkpoint = row['type'] in checkpoint_types
            node, created = Node.objects.update_or_create(
                node_id=row['node_id'],
                defaults={
                    'building': building,
                    'block': row['block'],
                    'name': row['name'],
                    'type': row['type'],
                    'floor': floor_map[row['floor']],
                    'x': row['x'],
                    'y': row['y'],
                    'qr_code': row['qr_code'],
                    'is_checkpoint': is_checkpoint,
                    'is_active': True,
                }
            )
            node_records[node.node_id] = node
            if created:
                created_nodes += 1
            else:
                updated_nodes += 1

            # Ensure QRCode record exists
            QRCode.objects.update_or_create(
                node=node,
                defaults={'payload': row['qr_code']}
            )

        # 4. Generate Indoor Topological Edges
        created_edges = self.generate_edges(node_records)

        return {
            'building': building.name,
            'floors_count': len(floor_map),
            'nodes_created': created_nodes,
            'nodes_updated': updated_nodes,
            'total_nodes': len(node_records),
            'edges_count': created_edges,
        }

    def generate_edges(self, node_map):
        """
        Creates bidirectional indoor walking edges and inter-floor lift/stairs transitions.
        """
        # Clear existing edges for nodes in this building to ensure clean idempotent state
        node_ids = list(node_map.keys())
        Edge.objects.filter(from_node__node_id__in=node_ids).delete()

        edges_to_create = []

        def add_bidirectional_edge(id_a, id_b, movement_type='walk', accessible=True, distance_override=None):
            if id_a not in node_map or id_b not in node_map:
                return
            nA = node_map[id_a]
            nB = node_map[id_b]

            if distance_override is not None:
                dist = distance_override
            else:
                dist = calculate_euclidean_distance(nA, nB, self.scale)

            # A -> B
            edges_to_create.append(Edge(
                from_node=nA,
                to_node=nB,
                distance=dist,
                movement_type=movement_type,
                accessible=accessible,
                is_active=True
            ))
            # B -> A
            edges_to_create.append(Edge(
                from_node=nB,
                to_node=nA,
                distance=dist,
                movement_type=movement_type,
                accessible=accessible,
                is_active=True
            ))

        # --- Floor 1 Topology ---
        # Entrance to Reception to Junction to Rooms
        add_bidirectional_edge('F1_N01', 'F1_N02')  # Main Entrance <-> Reception
        add_bidirectional_edge('F1_N02', 'F1_N03')  # Reception <-> Main Junction
        add_bidirectional_edge('F1_N03', 'F1_N04')  # Main Junction <-> Room 101
        add_bidirectional_edge('F1_N04', 'F1_N05')  # Room 101 <-> Room 102
        add_bidirectional_edge('F1_N03', 'F1_N06')  # Main Junction <-> Corridor Junction A
        add_bidirectional_edge('F1_N06', 'F1_N07')  # Corridor Junction A <-> Room 103
        add_bidirectional_edge('F1_N07', 'F1_N08')  # Room 103 <-> Room 104
        add_bidirectional_edge('F1_N06', 'F1_N09')  # Corridor Junction A <-> Staircase A
        add_bidirectional_edge('F1_N09', 'F1_N11')  # Staircase A <-> Corridor Junction B
        add_bidirectional_edge('F1_N11', 'F1_N10')  # Corridor Junction B <-> Lift A
        add_bidirectional_edge('F1_N10', 'F1_N12')  # Lift A <-> Restroom
        add_bidirectional_edge('F1_N07', 'F1_N11')  # Room 103 <-> Corridor Junction B
        add_bidirectional_edge('F1_N08', 'F1_N10')  # Room 104 <-> Lift A

        # --- Floor 2 Topology ---
        # y=75 line
        add_bidirectional_edge('F2_N04', 'F2_N01')  # Room 201 <-> Staircase A
        add_bidirectional_edge('F2_N01', 'F2_N03')  # Staircase A <-> Main Junction
        add_bidirectional_edge('F2_N03', 'F2_N02')  # Main Junction <-> Lift A
        add_bidirectional_edge('F2_N02', 'F2_N11')  # Lift A <-> Restroom
        # y=50 line
        add_bidirectional_edge('F2_N05', 'F2_N06')  # Room 202 <-> Room 203
        add_bidirectional_edge('F2_N06', 'F2_N07')  # Room 203 <-> Room 204
        # y=25 line
        add_bidirectional_edge('F2_N08', 'F2_N09')  # Lab 1 <-> Lab 2
        add_bidirectional_edge('F2_N09', 'F2_N10')  # Lab 2 <-> Seminar Hall
        # Vertical corridor columns
        add_bidirectional_edge('F2_N04', 'F2_N05')  # Room 201 <-> Room 202
        add_bidirectional_edge('F2_N05', 'F2_N08')  # Room 202 <-> Lab 1
        add_bidirectional_edge('F2_N03', 'F2_N06')  # Main Junction <-> Room 203
        add_bidirectional_edge('F2_N06', 'F2_N09')  # Room 203 <-> Lab 2
        add_bidirectional_edge('F2_N02', 'F2_N07')  # Lift A <-> Room 204
        add_bidirectional_edge('F2_N07', 'F2_N10')  # Room 204 <-> Seminar Hall

        # --- Floor 3 Topology ---
        # y=75 line
        add_bidirectional_edge('F3_N04', 'F3_N01')  # Room 301 <-> Staircase A
        add_bidirectional_edge('F3_N01', 'F3_N03')  # Staircase A <-> Main Junction
        add_bidirectional_edge('F3_N03', 'F3_N02')  # Main Junction <-> Lift A
        add_bidirectional_edge('F3_N02', 'F3_N11')  # Lift A <-> Restroom
        # y=50 line
        add_bidirectional_edge('F3_N05', 'F3_N06')  # Room 302 <-> Faculty Room
        add_bidirectional_edge('F3_N06', 'F3_N07')  # Faculty Room <-> Project Lab
        # y=25 line
        add_bidirectional_edge('F3_N08', 'F3_N09')  # Research Lab <-> Conference Room
        add_bidirectional_edge('F3_N09', 'F3_N10')  # Conference Room <-> Department Office
        # Vertical corridor columns
        add_bidirectional_edge('F3_N04', 'F3_N05')  # Room 301 <-> Room 302
        add_bidirectional_edge('F3_N05', 'F3_N08')  # Room 302 <-> Research Lab
        add_bidirectional_edge('F3_N03', 'F3_N06')  # Main Junction <-> Faculty Room
        add_bidirectional_edge('F3_N06', 'F3_N09')  # Faculty Room <-> Conference Room
        add_bidirectional_edge('F3_N02', 'F3_N07')  # Lift A <-> Project Lab
        add_bidirectional_edge('F3_N07', 'F3_N10')  # Project Lab <-> Department Office

        # --- Vertical Inter-Floor Connections ---
        # Staircase A transitions (Not wheelchair accessible)
        add_bidirectional_edge('F1_N09', 'F2_N01', movement_type='stairs', accessible=False, distance_override=self.floor_penalty)
        add_bidirectional_edge('F2_N01', 'F3_N01', movement_type='stairs', accessible=False, distance_override=self.floor_penalty)
        add_bidirectional_edge('F1_N09', 'F3_N01', movement_type='stairs', accessible=False, distance_override=self.floor_penalty * 1.9)

        # Lift A transitions (Wheelchair accessible)
        add_bidirectional_edge('F1_N10', 'F2_N02', movement_type='lift', accessible=True, distance_override=10.0)
        add_bidirectional_edge('F2_N02', 'F3_N02', movement_type='lift', accessible=True, distance_override=10.0)
        add_bidirectional_edge('F1_N10', 'F3_N02', movement_type='lift', accessible=True, distance_override=16.0)

        Edge.objects.bulk_create(edges_to_create)
        return len(edges_to_create)
