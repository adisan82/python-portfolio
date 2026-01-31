# -*- coding: utf-8 -*-
"""
nebula_graph.core.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

System wyjątków dla Silnika Grafowego Nebula.
Projektujemy hierarchię błędów tak, aby odseparować błędy logiczne (np. brak węzła)
od błędów systemowych (np. brak pamięci, błąd IO, błąd konsensusu Raft).

Główna zasada:
    - Fail Fast w przypadku niespójności grafu.
    - Retry Logic w przypadku konfliktów transakcyjnych (Optimistic Locking).
"""

class NebulaError(Exception):
    """Bazowa klasa dla wszystkich wyjątków wewnątrz Nebula Graph."""
    pass


class GraphTopologyError(NebulaError):
    """
    Rzucany, gdy operacja naruszyłaby spójność topologiczną.
    Np. Próba usunięcia węzła, który posiada aktywne krawędzie (bez flagi CASCADE).
    """
    pass


class NodeNotFoundError(GraphTopologyError):
    """Krytyczny błąd indeksu: odwołanie do nieistniejącego Node ID."""
    pass


class EdgeNotFoundError(GraphTopologyError):
    """Próba trawersowania lub modyfikacji nieistniejącej krawędzi."""
    pass


class SchemaViolationError(NebulaError):
    """
    Narusznie więzów integralności danych (Schema constraints).
    Np. próba dodania właściwości o złym typie do węzła zdefiniowanego w Schema.
    Nebula jest schemaless by default, ale wspiera opcjonalne typowanie.
    """
    pass


class TransactionConflictError(NebulaError):
    """
    Błąd współbieżności MVCC (Multi-Version Concurrency Control).
    Rzucany, gdy dwie transakcje próbują zmodyfikować ten sam podgraf w tym samym czasie.
    Klient powinien ponowić operację (Retry).
    """
    pass


class QuerySyntaxError(NebulaError):
    """Błąd parsera GQL (Graph Query Language)."""
    pass


class ResourceExhaustedError(NebulaError):
    """
    Ochrona przed OOM (Out Of Memory).
    Rzucany, gdy graf przekroczy limit węzłów w pamięci (Capacity Planning).
    """
    pass
