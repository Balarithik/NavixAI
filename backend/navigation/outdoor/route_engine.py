"""
Outdoor pedestrian routing engine (Dijkstra over the campus graph).
Response shape mirrors the indoor engine so the frontend can share UI.
"""
import math
from django.conf import settings

from navigation.routing.dijkstra import DijkstraRouter
from .graph import OutdoorGraphService


class OutdoorRouteEngine:
    def __init__(self, graph=None):
        self.graph = graph or OutdoorGraphService.build_graph()
        self.router = DijkstraRouter(self.graph)
        self.walking_speed_mps = getattr(settings, 'WALKING_SPEED_MPS', 1.2)

    def calculate_route(self, from_node_id, to_node_id):
        if from_node_id not in self.graph.nodes:
            raise ValueError(f"Outdoor origin '{from_node_id}' not found")
        if to_node_id not in self.graph.nodes:
            raise ValueError(f"Outdoor destination '{to_node_id}' not found")

        from_node = self.graph.nodes[from_node_id]
        to_node = self.graph.nodes[to_node_id]

        result = self.router.find_shortest_path(from_node_id, to_node_id, mode='any')
        if not result['found']:
            return {
                'success': False,
                'message': f"No outdoor route found between {from_node.name} and {to_node.name}",
                'from': self._summary(from_node),
                'to': self._summary(to_node),
            }

        path_nodes = result['path_nodes']
        total_distance = result['total_distance']
        duration_minutes = max(1, math.ceil(total_distance / self.walking_speed_mps / 60))

        path = [self._summary(n) for n in path_nodes]
        instructions = self._instructions(path_nodes)
        checkpoints = [
            {
                'index': i,
                'node_id': n.node_id,
                'name': n.name,
                'type': n.type,
                'is_start': i == 0,
                'is_destination': i == len(path_nodes) - 1,
            }
            for i, n in enumerate(path_nodes)
            if i in (0, len(path_nodes) - 1) or n.is_checkpoint or n.type in ('gate', 'building_entrance', 'junction')
        ]

        return {
            'success': True,
            'mode': 'outdoor',
            'from': self._summary(from_node),
            'to': self._summary(to_node),
            'distanceMetres': round(total_distance, 1),
            'durationMinutes': duration_minutes,
            'durationSeconds': round(total_distance / self.walking_speed_mps),
            'path': path,
            'instructions': instructions,
            'checkpoints': checkpoints,
        }

    @staticmethod
    def _summary(n):
        return {
            'node_id': n.node_id,
            'name': n.name,
            'type': n.type,
            'latitude': n.latitude,
            'longitude': n.longitude,
            'building_code': n.building.code if n.building else None,
        }

    @staticmethod
    def _instructions(path_nodes):
        if not path_nodes:
            return []
        steps = [f"Start at {path_nodes[0].name}"]
        for n in path_nodes[1:-1]:
            if n.type == 'gate':
                steps.append(f"Pass through {n.name}")
            elif n.type == 'junction':
                steps.append(f"Continue through {n.name}")
            elif n.type == 'building_entrance':
                steps.append(f"Head towards {n.name}")
            else:
                steps.append(f"Continue to {n.name}")
        if len(path_nodes) > 1:
            steps.append(f"Arrive at {path_nodes[-1].name}")
        return steps
