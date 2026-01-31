# -*- coding: utf-8 -*-
"""
nebula_graph.main
~~~~~~~~~~~~~~~~~

Punkt wejścia i Demo integracyjne dla systemu Nebula Graph.
Demonstruje działanie pełnego stacku:
1. Storage (Nodes/Edges)
2. Indexing (Property Index)
3. Parsing (GQL)
4. Execution (Basic Runtime)

To jest "Glue Code", który skleja komponenty w działającą bazę.
"""

import logging
import sys
import time
from typing import List, Dict, Any

from nebula_graph.core.storage import GraphStorage
from nebula_graph.core.algorithms import GraphTraversal
from nebula_graph.index.inverted import IndexManager
from nebula_graph.query.parser import QueryParser, QueryAST

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("nebula.main")

class ExecutionEngine:
    """
    Prosty silnik wykonawczy, który bierze AST i wykonuje operacje na Storage.
    W pełnej wersji byłby tu Cost-Based Optimizer.
    """
    def __init__(self, storage: GraphStorage, index_mgr: IndexManager):
        self.storage = storage
        self.index_mgr = index_mgr

    def execute(self, query_text: str) -> List[Any]:
        logger.info(f"Executing GQL: {query_text}")
        
        # 1. Parse
        parser = QueryParser(query_text)
        ast = parser.parse()
        
        # 2. Plan (Naive)
        # Szukamy punktu startowego. Obecnie obsługujemy tylko proste 'MATCH (n:Label) WHERE ...'
        results = []
        
        for match_clause in ast.matches:
            # Strategia wykonania:
            # A. Jeśli jest WHERE n.prop = val ORAZ mamy indeks -> Index Lookup (O(1))
            # B. Jeśli nie ma indeksu -> Label Scan (O(N_label))
            # C. Jeśli nie ma labela -> Full Scan (O(N_total))
            
            candidates = set()
            scan_method = "Full Scan"
            
            # Sprawdzamy WHERE pod kątem indeksów
            if ast.where and ast.where.variable == match_clause.variable:
                prop = ast.where.property_name
                val = ast.where.value
                
                # Próba użycia indeksu
                idx_hits = self.index_mgr.search(prop, val)
                if idx_hits:
                    scan_method = f"Index Seek ({prop}={val})"
                    candidates = idx_hits
                else:
                    # Fallback to full scan (mock)
                    # W prawdziwym systemie: iterujemy po iter_nodes() i filtrujemy
                    pass
            
            # Jeśli indeks nic nie dał (lub go nie było), robimy Full Memory Scan (wolne!)
            if not candidates:
                scan_method = "Memory Scan"
                for node in self.storage.iter_nodes():
                    # Check Labels
                    if match_clause.labels:
                        if not any(l in node.labels for l in match_clause.labels):
                            continue
                    
                    # Check Where (Filter)
                    if ast.where:
                        node_val = node.properties.get(ast.where.property_name)
                        if ast.where.operator == '=':
                            if node_val != ast.where.value:
                                continue
                                
                    candidates.add(node.id)
            
            logger.info(f"Plan: {scan_method} -> Found {len(candidates)} candidates")
            
            # Fetch objects
            for nid in candidates:
                results.append(self.storage.get_node(nid))
                
        return results

def main():
    print("""
    ========================================
       NEBULA GRAPH DATABASE v0.1 (Alpha)
    ========================================
    Initializing Kernel...
    """)
    
    # 1. Init Subsystems
    store = GraphStorage(capacity_limit=1_000_000)
    indices = IndexManager()
    
    # 2. Create Index on 'name'
    indices.create_index("name")
    
    # 3. Load Sample Data (Knowledge Graph)
    logger.info("Loading seed data...")
    
    # Node 1: Alice
    n1 = store.add_node(labels=["Person"], name="Alice", age=30)
    indices.on_node_created(n1)
    
    # Node 2: Bob
    n2 = store.add_node(labels=["Person"], name="Bob", age=34)
    indices.on_node_created(n2)
    
    # Node 3: OpenAI
    n3 = store.add_node(labels=["Company"], name="OpenAI", sector="AI")
    indices.on_node_created(n3)
    
    # Edges
    store.add_edge(n1.id, n3.id, "WORKS_AT", since=2020)
    store.add_edge(n2.id, n1.id, "KNOWS", weight=0.9)
    
    logger.info(store.stats())
    
    # 4. Execute Queries
    engine = ExecutionEngine(store, indices)
    
    # Query 1: Index Seek
    q1 = "MATCH (p:Person) WHERE p.name = 'Alice' RETURN p"
    res1 = engine.execute(q1)
    print(f"\nQuery 1 Result: {res1}\n")
    
    # Query 2: Traversal (Manual demo)
    print("--- Graph Traversal Demo (Alice's Network) ---")
    alice_id = res1[0].id
    for nid, depth in GraphTraversal.bfs(store, alice_id):
        node = store.get_node(nid)
        print(f"  [Depth {depth}] Node: {node.properties.get('name', 'N/A')} ({list(node.labels)})")
        
    print("\nNebula Graph is ready for Distributed Raft Protocol (Project Phase 4).\n")

if __name__ == "__main__":
    main()
