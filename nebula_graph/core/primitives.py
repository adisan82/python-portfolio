# -*- coding: utf-8 -*-
"""
nebula_graph.core.primitives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Definicja prymitywów grafowych: Węzłów (Nodes) i Krawędzi (Edges).

Performance Engineering:
    - Używamy `__slots__` wszędzie. Węzłów mogą być miliardy. Zaoszczędzenie
      `__dict__` (ok. 100 bajtów per obiekt) daje GB oszczędności przy dużej skali.
    - ID są 64-bitowymi integerami (Snowflake generation capability).
    - Właściwości (Properties) są trzymane w osobnych strukturach (Columnar Storage mockup),
      ale tutaj dla uproszczenia wewnątrz obiektu (z opcją compact dict).

Relacje:
    Nebula jest grafem skierowanym (Directed Propert Graph).
"""

import time
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field

# Typ aliasy dla czytelności sygnatur
NodeID = int
EdgeID = int
Label = str

class GraphObject:
    """
    Abstrakcyjna baza dla elementów grafu.
    Obsługuje mechanizm właściwości (Properties).
    """
    __slots__ = ()
    
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


class Node(GraphObject):
    """
    Wierzchołek grafu (Vertex).
    
    Attributes:
        id (int): Unikalny identyfikator (64-bit).
        labels (Set[str]): Zbiór etykiet (np. "Person", "Employee").
        properties (Dict): Daneużytkowe (Payload).
    """
    # Restrykcyjna alokacja pamięci
    __slots__ = ('id', 'labels', 'properties', '_version')

    def __init__(self, node_id: NodeID, labels: Optional[List[str]] = None, **kwargs):
        self.id = node_id
        # Set jest szybki do sprawdzania 'x in labels', ale bierze trochę RAMu.
        # W wersji ultra-low-mem użylibyśmy BitMapy (BitSet) dla znanych labeli.
        self.labels: Set[Label] = set(labels) if labels else set()
        self.properties: Dict[str, Any] = kwargs
        self._version = 0 # Dla MVCC (Optymistyczne blokowanie)

    def add_label(self, label: Label):
        self.labels.add(label)
        self._version += 1

    def remove_label(self, label: Label):
        self.labels.discard(label)
        self._version += 1

    def __repr__(self):
        return f"<Node(id={self.id}, labels={list(self.labels)}, props={self.properties})>"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Node) and self.id == other.id


class Edge(GraphObject):
    """
    Krawędź skierowana (Directed Relationship).
    Łączy dwa węzły: Source Node -> Target Node.
    
    Attributes:
        src (int): ID węzła źródłowego.
        dst (int): ID węzła docelowego.
        type (str): Typ relacji (np. "KNOWS", "PURCHASED").
    """
    __slots__ = ('id', 'src', 'dst', 'type', 'properties', 'weight')

    def __init__(self, edge_id: EdgeID, src: NodeID, dst: NodeID, rel_type: str, weight: float = 1.0, **kwargs):
        self.id = edge_id
        self.src = src
        self.dst = dst
        self.type = rel_type
        self.weight = weight # Dla algorytmów ważonych (Dijkstra)
        self.properties: Dict[str, Any] = kwargs

    def __repr__(self):
        return f"<Edge({self.src} -[:{self.type}]-> {self.dst})>"
    
    def __hash__(self):
        return hash(self.id)


@dataclass(frozen=True)
class Path:
    """
    Reprezentacja ścieżki w grafie (wynik trawersowania).
    Niemutowalna (Immutable) dla bezpieczeństwa w generatorach.
    """
    nodes: List[Node]
    edges: List[Edge]
    cost: float = 0.0

    def __len__(self):
        return len(self.edges)
