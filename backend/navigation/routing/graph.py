"""
Graph construction service for NavixAI.
Builds in-memory graph structure from Node and Edge database models.
"""

from collections import defaultdict
from navigation.models import Node, Edge


class NavigationGraph:
    def __init__(self):
        # adj[u] = list of (v, weight, edge_obj)
        self.adj = defaultdict(list)
        self.nodes = {}

    def add_node(self, node):
        self.nodes[node.node_id] = node

    def add_edge(self, edge):
        self.adj[edge.from_node.node_id].append((
            edge.to_node.node_id,
            edge.distance,
            edge
        ))

    def get_neighbors(self, node_id, mode='any'):
        """
        Returns neighbors of node_id matching movement_type filter:
        - mode == 'lift': excludes stairs
        - mode == 'stairs': excludes lift
        - mode == 'any': includes all
        """
        neighbors = []
        for neighbor_id, weight, edge in self.adj.get(node_id, []):
            if not edge.is_active:
                continue

            if mode == 'lift' and edge.movement_type == 'stairs':
                continue
            elif mode == 'stairs' and edge.movement_type == 'lift':
                continue

            neighbors.append((neighbor_id, weight, edge))
        return neighbors


class GraphService:
    @staticmethod
    def build_graph():
        """Constructs NavigationGraph from active database records."""
        graph = NavigationGraph()
        nodes = Node.objects.filter(is_active=True).select_related('floor', 'building')
        for node in nodes:
            graph.add_node(node)

        edges = Edge.objects.filter(is_active=True).select_related('from_node', 'to_node', 'from_node__floor', 'to_node__floor')
        for edge in edges:
            graph.add_edge(edge)

        return graph
