# -*- coding: utf-8 -*-
"""
simulation.py
~~~~~~~~~~~~~

Skrypt symulacyjny uruchamiający klaster 3 węzłów Helix lokalnie.
Demonstruje algorytm wyboru lidera w czasie rzeczywistym.

Uwaga:
    To uruchamia 3 pętle zdarzeń asyncio w JEDNYM procesie przy użyciu `asyncio.gather`
    dla uproszczenia demo. W produkcji każdy węzeł to osobny proces/container.
"""

import asyncio
import logging
import sys

from helix.node import RaftNode

async def main():
    print("--- HELIX CONSENSUS SIMULATION ---")
    print("Spawning 3 Nodes Local Cluster...")
    
    # Konfiguracja portów: 1:9001, 2:9002, 3:9003
    peers_map = {
        1: 9001,
        2: 9002,
        3: 9003
    }
    
    nodes = []
    
    # Inicjalizacja węzłów
    for node_id, port in peers_map.items():
        # Peers dla danego węzła to wszyscy inni
        my_peers = {pid: p for pid, p in peers_map.items() if pid != node_id}
        
        node = RaftNode(node_id, my_peers)
        nodes.append(node)
        
        # Start
        await node.start(port)
        
    print("Cluster started. Watch logs for Leader Election...")
    print("Press Ctrl+C to stop.")
    
    # Utrzymanie procesu
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            # Windows Selector fix
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
