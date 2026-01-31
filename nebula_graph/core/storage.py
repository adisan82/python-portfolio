# -*- coding: utf-8 -*-
"""
nebula_graph.core.storage
~~~~~~~~~~~~~~~~~~~~~~~~~

Silnik przechowywania grafu w pamięci (In-Memory Graph Store).
Implementuje hybrydowe podejście: Adjacency List + Reverse Index.

Struktury Danych:
    - `nodes`: HashMapa {NodeID -> Node}. O(1) Access.
    - `out_edges`: {NodeID -> List[Edge]}. Szybkie wyjścia (Traversal).
    - `in_edges`: {NodeID -> List[Edge]}. Szybkie wejścia (Reverse Traversal / Backtracking).

Concurrency:
    - W tej warstwie używamy RLock (Reentrant Lock) dla thread-safety.
    - W wersji Distributed (Phase 4) dojdzie Raft Log.
"""

import threading
import logging
from typing import Dict, List, Optional, Generator, Iterator, Tuple
from collections import defaultdict

from .primitives import Node, Edge, NodeID, EdgeID
from .exceptions import NodeNotFoundError, EdgeNotFoundError, ResourceExhaustedError

logger = logging.getLogger("nebula.storage")

class GraphStorage:
    """
    Centralny magazyn grafu.
    Zarządza cyklem życia węzłów i krawędzi.
    """
    
    def __init__(self, capacity_limit: int = 10_000_000):
        self._nodes: Dict[NodeID, Node] = {}
        self._edges: Dict[EdgeID, Edge] = {}
        
        # Indeksy sąsiedztwa (Adjacency Lists)
        # defaultdict(list) jest szybki, ale zużywa sporo RAMu na puste listy.
        # Optymalizacja: alokujemy listę dopiero przy pierwszej krawędzi.
        self._out_edges: Dict[NodeID, List[Edge]] = {}
        self._in_edges: Dict[NodeID, List[Edge]] = {}
        
        # Liczniki ID (Sequences)
        self._node_seq = 0
        self._edge_seq = 0
        
        self._lock = threading.RLock()
        self.capacity_limit = capacity_limit
        
        logger.info(f"Graph Storage initialized. Capacity: {capacity_limit} nodes.")

    # --- CRUD Operations: Nodes ---

    def add_node(self, labels: List[str] = None, **properties) -> Node:
        """Tworzy i dodaje nowy węzeł do grafu."""
        with self._lock:
            if len(self._nodes) >= self.capacity_limit:
                raise ResourceExhaustedError("Graph capacity exceeded")

            self._node_seq += 1
            node = Node(self._node_seq, labels, **properties)
            self._nodes[node.id] = node
            return node

    def get_node(self, node_id: NodeID) -> Node:
        # Bez locka dla odczytu - zakładamy GIL atomicity dla dict access,
        # ale w true multi-threading python to ryzykowne dla consistency.
        # Tu dla wydajności pomijamy lock (Read Heavy workload).
        try:
            return self._nodes[node_id]
        except KeyError:
            raise NodeNotFoundError(f"Node {node_id} does not exist")

    def delete_node(self, node_id: NodeID, cascade: bool = False):
        """
        Usuwa węzeł.
        Jeśli cascade=True, usuwa też przyległe krawędzie.
        W przeciwnym razie rzuca błąd, jeśli węzeł ma krawędzie.
        """
        with self._lock:
            if node_id not in self._nodes:
                raise NodeNotFoundError(f"Node {node_id} not found")

            # Sprawdzenie krawędzi
            has_edges = (node_id in self._out_edges) or (node_id in self._in_edges)
            
            if has_edges:
                if not cascade:
                    raise IsADirectoryError(f"Node {node_id} has edges. Use cascade=True.")
                else:
                    # Cascade delete logic
                    # 1. Usuń wychodzące
                    out_edges = self._out_edges.pop(node_id, [])
                    for edge in out_edges:
                        self._remove_inverse_edge_ref(self._in_edges, edge.dst, edge)
                        del self._edges[edge.id]
                    
                    # 2. Usuń przychodzące
                    in_edges = self._in_edges.pop(node_id, [])
                    for edge in in_edges:
                        self._remove_inverse_edge_ref(self._out_edges, edge.src, edge)
                        del self._edges[edge.id]
            
            del self._nodes[node_id]

    # --- CRUD Operations: Edges ---

    def add_edge(self, src_id: NodeID, dst_id: NodeID, rel_type: str, weight: float = 1.0, **props) -> Edge:
        with self._lock:
            # Walidacja istnienia węzłów
            if src_id not in self._nodes:
                raise NodeNotFoundError(f"Source Node {src_id} missing")
            if dst_id not in self._nodes:
                raise NodeNotFoundError(f"Target Node {dst_id} missing")

            self._edge_seq += 1
            edge = Edge(self._edge_seq, src_id, dst_id, rel_type, weight, **props)
            self._edges[edge.id] = edge
            
            # Aktualizacja list sąsiedztwa
            self._add_to_adj_list(self._out_edges, src_id, edge)
            self._add_to_adj_list(self._in_edges, dst_id, edge)
            
            return edge

    # --- Private Helpers ---

    def _add_to_adj_list(self, adj: Dict[NodeID, List[Edge]], key: NodeID, edge: Edge):
        if key not in adj:
            adj[key] = []
        adj[key].append(edge)

    def _remove_inverse_edge_ref(self, adj: Dict[NodeID, List[Edge]], key: NodeID, edge: Edge):
        """Bezpieczne usuwanie referencji krawędzi z listy."""
        if key in adj:
            try:
                # To jest O(N) dla stopnia węzła. 
                # Dla superwęzłów (Supernodes) trzeba by użyć Set lub Linked List.
                adj[key].remove(edge)
                if not adj[key]:
                    del adj[key]
            except ValueError:
                pass


    # --- Traversal Primitives (Iterators) ---

    def iter_nodes(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def iter_out_edges(self, node_id: NodeID, type_filter: Optional[str] = None) -> Iterator[Edge]:
        """
        Szybki iterator po krawędziach wychodzących.
        Używany przez BFS/DFS.
        """
        edges = self._out_edges.get(node_id, [])
        if type_filter:
            for e in edges:
                if e.type == type_filter:
                    yield e
        else:
            yield from edges

    def stats(self) -> str:
        with self._lock:
            return f"Graph Nodes: {len(self._nodes)}, Edges: {len(self._edges)}"
