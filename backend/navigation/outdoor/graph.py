"""
Outdoor campus graph built from OutdoorNode / OutdoorEdge records.
Reuses the generic DijkstraRouter from the indoor engine.
"""
import math
from collections import defaultdict

from navigation.models import OutdoorNode, OutdoorEdge


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


class OutdoorGraph:
    def __init__(self):
        self.adj = defaultdict(list)
        self.nodes = {}

    def add_node(self, node):
        self.nodes[node.node_id] = node

    def add_edge(self, edge):
        weight = edge.distance_m
        if not weight or weight <= 0:
            a, b = edge.from_node, edge.to_node
            weight = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
        self.adj[edge.from_node.node_id].append((edge.to_node.node_id, weight, edge))

    def get_neighbors(self, node_id, mode='any'):
        neighbors = []
        for nid, weight, edge in self.adj.get(node_id, []):
            if not edge.is_active:
                continue
            neighbors.append((nid, weight, edge))
        return neighbors


class OutdoorGraphService:
    @staticmethod
    def build_graph():
        graph = OutdoorGraph()
        for node in OutdoorNode.objects.filter(is_active=True).select_related('building'):
            graph.add_node(node)
        edges = OutdoorEdge.objects.filter(is_active=True).select_related('from_node', 'to_node')
        for edge in edges:
            if edge.from_node.is_active and edge.to_node.is_active:
                graph.add_edge(edge)
        return graph
