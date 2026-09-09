"""
Dijkstra Shortest-Path Algorithm implementation for NavixAI.
"""

import heapq


class DijkstraRouter:
    def __init__(self, graph):
        self.graph = graph

    def find_shortest_path(self, start_node_id, target_node_id, mode='any'):
        """
        Finds shortest path between start_node_id and target_node_id.
        mode can be 'any', 'lift', or 'stairs'.
        Returns:
            dict with:
                - found: bool
                - path_node_ids: list of node IDs
                - path_nodes: list of Node model instances
                - path_edges: list of Edge model instances
                - total_distance: float
        """
        if start_node_id not in self.graph.nodes:
            raise ValueError(f"Start node '{start_node_id}' does not exist in navigation graph")
        if target_node_id not in self.graph.nodes:
            raise ValueError(f"Target node '{target_node_id}' does not exist in navigation graph")

        if start_node_id == target_node_id:
            start_node = self.graph.nodes[start_node_id]
            return {
                'found': True,
                'path_node_ids': [start_node_id],
                'path_nodes': [start_node],
                'path_edges': [],
                'total_distance': 0.0,
            }

        # Priority queue stores tuples: (accumulated_dist, current_node_id)
        pq = [(0.0, start_node_id)]
        distances = {start_node_id: 0.0}
        previous = {}  # node_id -> (prev_node_id, edge_obj)

        while pq:
            current_dist, current_id = heapq.heappop(pq)

            if current_id == target_node_id:
                break

            if current_dist > distances.get(current_id, float('inf')):
                continue

            for neighbor_id, edge_weight, edge_obj in self.graph.get_neighbors(current_id, mode=mode):
                new_dist = current_dist + edge_weight

                if new_dist < distances.get(neighbor_id, float('inf')):
                    distances[neighbor_id] = new_dist
                    previous[neighbor_id] = (current_id, edge_obj)
                    heapq.heappush(pq, (new_dist, neighbor_id))

        if target_node_id not in previous:
            return {
                'found': False,
                'path_node_ids': [],
                'path_nodes': [],
                'path_edges': [],
                'total_distance': 0.0,
            }

        # Reconstruct path backwards
        path_node_ids = []
        path_edges = []
        curr = target_node_id

        while curr != start_node_id:
            path_node_ids.append(curr)
            prev_id, edge = previous[curr]
            path_edges.append(edge)
            curr = prev_id

        path_node_ids.append(start_node_id)
        path_node_ids.reverse()
        path_edges.reverse()

        path_nodes = [self.graph.nodes[nid] for nid in path_node_ids]
        total_dist = distances[target_node_id]

        return {
            'found': True,
            'path_node_ids': path_node_ids,
            'path_nodes': path_nodes,
            'path_edges': path_edges,
            'total_distance': round(total_dist, 2),
        }
