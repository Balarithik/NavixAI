"""
High-level Route Engine for NavixAI.
Orchestrates Dijkstra routing, floor transition analysis, ETA calculation,
checkpoints generation, and instruction generation.
"""

import math
from django.conf import settings
from navigation.models import Node
from .graph import GraphService
from .dijkstra import DijkstraRouter
from .instruction_generator import generate_instructions


class RouteEngine:
    def __init__(self, graph=None):
        self.graph = graph or GraphService.build_graph()
        self.router = DijkstraRouter(self.graph)
        self.walking_speed_mps = getattr(settings, 'WALKING_SPEED_MPS', 1.2)

    def calculate_route(self, from_node_id, to_node_id, mode='any'):
        """
        Calculates optimal route from from_node_id to to_node_id.
        mode: 'any' (default), 'lift', or 'stairs'.
        """
        if from_node_id not in self.graph.nodes:
            raise ValueError(f"Origin location '{from_node_id}' not found")
        if to_node_id not in self.graph.nodes:
            raise ValueError(f"Destination '{to_node_id}' not found")

        from_node = self.graph.nodes[from_node_id]
        to_node = self.graph.nodes[to_node_id]

        requires_floor_transition = (from_node.floor.floor_number != to_node.floor.floor_number)

        # Check if both lift and stairs alternatives exist across floors
        has_lift_option = False
        has_stairs_option = False
        if requires_floor_transition:
            lift_check = self.router.find_shortest_path(from_node_id, to_node_id, mode='lift')
            stairs_check = self.router.find_shortest_path(from_node_id, to_node_id, mode='stairs')
            has_lift_option = lift_check['found']
            has_stairs_option = stairs_check['found']

        both_options_available = (has_lift_option and has_stairs_option)

        # Compute the actual path using requested mode
        result = self.router.find_shortest_path(from_node_id, to_node_id, mode=mode)

        if not result['found']:
            return {
                'success': False,
                'message': f"No valid route found between {from_node.name} and {to_node.name} using mode '{mode}'",
                'from': self._serialize_node_summary(from_node),
                'to': self._serialize_node_summary(to_node),
            }

        path_nodes = result['path_nodes']
        path_edges = result['path_edges']
        total_distance = result['total_distance']

        # Determine floors crossed
        floors_visited = []
        for n in path_nodes:
            f_num = n.floor.floor_number
            if f_num not in floors_visited:
                floors_visited.append(f_num)

        # Determine vertical mode used
        vertical_mode_used = None
        for edge in path_edges:
            if edge.movement_type in ('lift', 'stairs'):
                vertical_mode_used = edge.movement_type
                break

        # Calculate estimated walking time (in seconds and minutes)
        # Add 30 seconds for lift wait or stairs climb per floor
        floor_transitions_count = max(0, len(floors_visited) - 1)
        walk_time_seconds = total_distance / self.walking_speed_mps
        wait_penalty_seconds = floor_transitions_count * (25 if vertical_mode_used == 'lift' else 35)
        total_time_seconds = walk_time_seconds + wait_penalty_seconds
        duration_minutes = max(1, math.ceil(total_time_seconds / 60))

        # Human instructions
        instructions = generate_instructions(path_nodes, path_edges)

        # Checkpoints along path
        checkpoints = []
        accumulated_dist = 0.0
        for i, n in enumerate(path_nodes):
            if i > 0:
                accumulated_dist += path_edges[i - 1].distance

            # Mark if checkpoint, or start/destination, or floor transition
            is_start = (i == 0)
            is_end = (i == len(path_nodes) - 1)
            is_transition = False
            if i < len(path_edges) and path_edges[i].movement_type in ('lift', 'stairs'):
                is_transition = True

            if is_start or is_end or n.is_checkpoint or is_transition:
                checkpoints.append({
                    'index': i,
                    'node_id': n.node_id,
                    'name': n.name,
                    'floor': n.floor.floor_number,
                    'type': n.type,
                    'distance_from_start': round(accumulated_dist, 1),
                    'is_start': is_start,
                    'is_destination': is_end,
                    'is_transition': is_transition,
                })

        # Serialized path points for map rendering
        serialized_path = [
            {
                'node_id': n.node_id,
                'name': n.name,
                'floor': n.floor.floor_number,
                'floor_name': n.floor.name,
                'type': n.type,
                'x': n.x,
                'y': n.y,
            }
            for n in path_nodes
        ]

        return {
            'success': True,
            'from': self._serialize_node_summary(from_node),
            'to': self._serialize_node_summary(to_node),
            'distanceMetres': round(total_distance, 1),
            'durationMinutes': duration_minutes,
            'durationSeconds': round(total_time_seconds),
            'floorsCrossed': floor_transitions_count,
            'floorsVisited': floors_visited,
            'verticalMode': vertical_mode_used or 'walk',
            'requiresFloorTransition': requires_floor_transition,
            'liftStairChoiceAvailable': both_options_available,
            'activeMode': mode,
            'path': serialized_path,
            'instructions': instructions,
            'checkpoints': checkpoints,
        }

    def _serialize_node_summary(self, node):
        return {
            'node_id': node.node_id,
            'name': node.name,
            'type': node.type,
            'building_code': node.building.code,
            'building_name': node.building.name,
            'floor': node.floor.floor_number,
            'floor_name': node.floor.name,
            'x': node.x,
            'y': node.y,
        }
