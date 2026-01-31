# -*- coding: utf-8 -*-
"""
nebula_graph.core.algorithms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementacja algorytmów trawersowania grafu.
Wykorzystujemy lazy evaluation (Generatory) gdzie tylko się da, aby nie wczytywać
całych podgrafów do pamięci.

Algorithms:
    - BFS (Breadth-First Search): Do znajdowania najkrótszych ścieżek (w sensie liczby hopów).
    - DFS (Depth-First Search): Do eksploracji głębokiej (np. detekcja cykli).
    - Dijkstra: Najkrótsza ścieżka ważona (Weighted Shortest Path).
"""

import collections
import heapq
from typing import Iterator, List, Optional, Set, Dict, Tuple
from .storage import GraphStorage
from .primitives import NodeID, Edge, Path

class GraphTraversal:
    """Namespace dla algorytmów."""

    @staticmethod
    def bfs(graph: GraphStorage, start_node_id: NodeID, max_depth: int = 5) -> Iterator[Tuple[NodeID, int]]:
        """
        Generator BFS. Zwraca odwiedzane węzły poziomami.
        
        Yields:
            (node_id, depth)
        """
        visited = {start_node_id}
        queue = collections.deque([(start_node_id, 0)])
        
        while queue:
            current_id, depth = queue.popleft()
            
            yield current_id, depth
            
            if depth < max_depth:
                # Pobierz sąsiadów
                # Używamy iter_out_edges dla wydajności (nie pobieramy całej listy)
                for edge in graph.iter_out_edges(current_id):
                    neighbor = edge.dst
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))

    @staticmethod
    def find_shortest_path_dijkstra(graph: GraphStorage, start_id: NodeID, target_id: NodeID) -> Optional[List[EdgeID]]:
        """
        Implementacja algorytmu Dijkstry z kolejką priorytetową (Binary Heap).
        Znajduje ścieżkę o najmniejszej sumie wag (edge.weight).
        
        Returns:
            List[EdgeID]: Lista ID krawędzi tworzących ścieżkę lub None.
        """
        # Priority Queue: (cost, current_node_id)
        pq = [(0.0, start_id)]
        
        # Mapa kosztów dojścia: {node_id -> min_cost}
        costs = {start_id: 0.0}
        
        # Mapa poprzedników do odtworzenia ścieżki: {node_id -> incoming_edge}
        backtrack: Dict[NodeID, Edge] = {}
        
        visited: Set[NodeID] = set()

        while pq:
            current_cost, u = heapq.heappop(pq)
            
            if u == target_id:
                # Sukces! Odtwarzamy ścieżkę wstecz.
                path_edges = []
                curr = target_id
                while curr != start_id:
                    edge = backtrack[curr]
                    path_edges.append(edge.id)
                    curr = edge.src
                return list(reversed(path_edges))

            if u in visited:
                continue
            visited.add(u)

            # Relaksacja krawędzi
            for edge in graph.iter_out_edges(u):
                v = edge.dst
                new_cost = current_cost + edge.weight
                
                if new_cost < costs.get(v, float('inf')):
                    costs[v] = new_cost
                    backtrack[v] = edge
                    heapq.heappush(pq, (new_cost, v))
        
        return None # Brak ścieżki
