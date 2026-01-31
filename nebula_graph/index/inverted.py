# -*- coding: utf-8 -*-
"""
nebula_graph.index.inverted
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementacja Odwróconego Indeksu (Inverted Index) dla szybkiego wyszukiwania właściwości.
W grafowych bazach danych (Property Graph) często musimy znaleźć węzły po atrybutach,
np. `WHERE n.name = 'Alice'`. Bez indeksu wymagałoby to pełnego skanu (Full Table Scan) - O(N).
Z indeksem mamy O(1) lub O(log N).

Strategia:
    - Globalny rejestr indeksów: `Dict[PropertyName, IndexStructure]`.
    - Każdy IndexStructure to mapa: `Value -> Set[NodeID]`.
    - Obsługa typów: String (Exact Match), Numeric (Range Queries - TODO: B-Tree/SkipList).
    
Concurrency:
    - Thread-safe (zabezpieczone RLockiem).
"""

import threading
import logging
from typing import Dict, Set, Any, List, Optional, Union
from collections import defaultdict
from ..core.primitives import NodeID

logger = logging.getLogger("nebula.index")

class PropertyIndex:
    """
    Struktura indeksująca jedną właściwość (Property).
    Działa jak Hash Index.
    """
    __slots__ = ('property_name', '_items', '_lock')

    def __init__(self, property_name: str):
        self.property_name = property_name
        # Value -> Set[NodeID]
        # Set jest kluczowy, bo wiele węzłów może mieć tę samą wartość (np. age=30).
        self._items: Dict[Any, Set[NodeID]] = defaultdict(set)
        self._lock = threading.RLock()

    def add(self, value: Any, node_id: NodeID):
        """Dodaje wpis do indeksu."""
        with self._lock:
            self._items[value].add(node_id)

    def remove(self, value: Any, node_id: NodeID):
        """Usuwa wpis z indeksu (np. przy aktualizacji węzła)."""
        with self._lock:
            if value in self._items:
                self._items[value].discard(node_id)
                # Garbage Collection: usuwamy klucz jeśli pusty set, oszczędzamy RAM
                if not self._items[value]:
                    del self._items[value]

    def lookup(self, value: Any) -> Set[NodeID]:
        """Zwraca zbiór ID węzłów pasujących do wartości."""
        # Bezpieczniej zwrócić kopię, żeby klient nie zepsuł wewnętrznego stanu
        # ale dla wydajności (Zero-Copy) w Pythonie przy odczycie zwracamy referencję
        # lub frozen set. Tutaj balansujemy: zwracamy kopię shallow.
        with self._lock:
            return set(self._items.get(value, []))

    def stats(self) -> str:
        return f"Index({self.property_name}): {len(self._items)} keys"


class IndexManager:
    """
    Zarządca wszystkich indeksów w bazie.
    Automatycznie aktualizuje indeksy przy wstawianiu danych (Trigger-like mechanism).
    """
    
    def __init__(self):
        self._indices: Dict[str, PropertyIndex] = {}
        self._lock = threading.RLock()

    def create_index(self, property_name: str):
        """Tworzy nowy indeks na danej właściwości."""
        with self._lock:
            if property_name in self._indices:
                logger.warning(f"Index on '{property_name}' already exists.")
                return
            
            logger.info(f"Building index for property: {property_name}")
            self._indices[property_name] = PropertyIndex(property_name)
            
            # W prawdziwej bazie tutaj nastąpiłby Background Indexing Job
            # (przejście po istniejących danych).

    def drop_index(self, property_name: str):
        with self._lock:
            if property_name in self._indices:
                del self._indices[property_name]
                logger.info(f"Dropped index: {property_name}")

    def on_node_created(self, node):
        """Hook wywoływany przez Storage Engine po utworzeniu węzła."""
        with self._lock:
            for prop, val in node.properties.items():
                if prop in self._indices:
                    self._indices[prop].add(val, node.id)

    def on_node_updated(self, node, old_props: Dict[str, Any]):
        """Hook aktualizujący indeksy. Wymaga wiedzy o poprzednim stanie."""
        # TODO: Implementacja logiki dirty checking.
        pass

    def search(self, property_name: str, value: Any) -> Set[NodeID]:
        """Fasada wyszukiwania."""
        # Lock na poziomie Managera tylko do pobrania referencji indeksu
        # Lock operacyjny jest wewnątrz PropertyIndex
        idx = self._indices.get(property_name)
        if idx:
            return idx.lookup(value)
        else:
            # Fallback warning
            logger.debug(f"Warning: Full scan required for {property_name} (No Index)")
            return set()
