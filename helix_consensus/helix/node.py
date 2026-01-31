# -*- coding: utf-8 -*-
"""
helix.node
~~~~~~~~~~

Główna maszyna stanów (Finite State Machine) Raft.
Implementuje logikę: Leader Election, Heartbeats, State Transitions.

Roles:
    - FOLLOWER: Słucha leadera. Jeśli timeout -> CANDIDATE.
    - CANDIDATE: Prosi o głosy. Jeśli większość -> LEADER.
    - LEADER: Wysyła Heartbeaty (AppendEntries empty).
"""

import asyncio
import random
import logging
import time
from enum import Enum, auto
from typing import List, Optional, Dict

from .rpc import Packet, MessageType
from .storage import RaftStorage

# Konfiguracja Loggera
logging.basicConfig(format='%(asctime)s [%(levelname)s] Node-%(node_name)s: %(message)s', level=logging.INFO)

class NodeState(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

class RaftProtocol(asyncio.DatagramProtocol):
    def __init__(self, node):
        self.node = node

    def connection_made(self, transport):
        self.node.transport = transport

    def datagram_received(self, data, addr):
        packet = Packet.unpack(data)
        if packet:
            self.node.handle_message(packet, addr)

class RaftNode:
    def __init__(self, node_id: int, peers: Dict[int, int]):
        """
        node_id: Moje ID (np. 1)
        peers: Mapa {id: port} innych węzłów.
        """
        self.node_id = node_id
        self.peers = peers # Map ID -> Port
        self.storage = RaftStorage(node_id)
        
        # State
        self.state = NodeState.FOLLOWER
        self.current_term, self.voted_for = self.storage.load_state()
        self.votes_received = 0
        self.leader_id = None
        
        # Timers
        self.election_deadline = 0.0
        self.heartbeat_interval = 0.5 # 500ms
        
        # AsyncIO
        self.transport = None
        self.logger = logging.getLogger("Raft")
        self.logger = logging.LoggerAdapter(self.logger, {'node_name': self.node_id})

    async def start(self, port: int):
        loop = asyncio.get_running_loop()
        self.logger.info(f"Starting on port {port} (Term {self.current_term})")
        
        # Bind UDP
        await loop.create_datagram_endpoint(
            lambda: RaftProtocol(self),
            local_addr=('127.0.0.1', port)
        )
        
        self.reset_election_timer()
        asyncio.create_task(self.run_loop())

    def reset_election_timer(self):
        # Randomized timeout: 1.5s - 3.0s
        # Zwiększamy slightly aby łatwiej obserwować w terminalu
        timeout = random.uniform(1.5, 3.0)
        self.election_deadline = time.time() + timeout

    async def run_loop(self):
        """Pętla główna (Main Loop)."""
        while True:
            now = time.time()
            
            if self.state == NodeState.FOLLOWER or self.state == NodeState.CANDIDATE:
                if now > self.election_deadline:
                    self.logger.warning("Election Timeout! Becoming CANDIDATE.")
                    await self.become_candidate()
            
            elif self.state == NodeState.LEADER:
                await self.broadcast_heartbeat()
                await asyncio.sleep(self.heartbeat_interval)
                
            await asyncio.sleep(0.1)

    async def become_candidate(self):
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id # Głos na siebie
        self.votes_received = 1
        self.storage.save_state(self.current_term, self.voted_for)
        
        self.reset_election_timer()
        
        # Request votes
        self.logger.info(f"Starting Election (Term {self.current_term}). Requesting votes...")
        pkg = Packet(MessageType.VOTE_REQ, self.current_term, self.node_id)
        self.broadcast(pkg)

    def broadcast(self, packet: Packet):
        data = packet.pack()
        for pid, port in self.peers.items():
            if self.transport:
                self.transport.sendto(data, ('127.0.0.1', port))

    async def broadcast_heartbeat(self):
        pkg = Packet(MessageType.APPEND_REQ, self.current_term, self.node_id)
        self.broadcast(pkg)

    def handle_message(self, pkg: Packet, addr):
        # 1. Update Term if older
        if pkg.term > self.current_term:
            self.logger.info(f"Discovered higher term {pkg.term} from Node {pkg.src_id}. Demoting to FOLLOWER.")
            self.current_term = pkg.term
            self.state = NodeState.FOLLOWER
            self.voted_for = None
            self.leader_id = None
            self.storage.save_state(self.current_term, None)
            self.reset_election_timer()

        # 2. Handle Message Types
        if pkg.msg_type == MessageType.VOTE_REQ:
            self._handle_vote_request(pkg, addr)
        
        elif pkg.msg_type == MessageType.VOTE_RESP:
            self._handle_vote_response(pkg)
            
        elif pkg.msg_type == MessageType.APPEND_REQ:
            self._handle_append_entries(pkg)

    def _handle_vote_request(self, pkg: Packet, addr):
        # Zasada: Udziel głosu jeśli (term >= current) ORAZ (nie głosowałem lub głosowałem na niego)
        vote_granted = False
        
        if pkg.term >= self.current_term:
            if self.voted_for is None or self.voted_for == pkg.src_id:
                self.voted_for = pkg.src_id
                self.storage.save_state(self.current_term, self.voted_for)
                vote_granted = True
                self.reset_election_timer() # Głosowanie resetuje timeout
        
        if vote_granted:
            self.logger.info(f"Voted FOR Node {pkg.src_id} in term {pkg.term}")
            resp = Packet(MessageType.VOTE_RESP, self.current_term, self.node_id)
            if self.transport:
                self.transport.sendto(resp.pack(), addr)

    def _handle_vote_response(self, pkg: Packet):
        if self.state == NodeState.CANDIDATE and pkg.term == self.current_term:
            self.votes_received += 1
            quorum = (len(self.peers) + 1) // 2 + 1
            
            if self.votes_received >= quorum:
                self.logger.info(f"Quorum reached ({self.votes_received} votes). Becoming LEADER!")
                self.state = NodeState.LEADER
                self.leader_id = self.node_id
                # Natychmiastowy heartbeat aby uciszyć innych
                asyncio.create_task(self.broadcast_heartbeat())

    def _handle_append_entries(self, pkg: Packet):
        # Heartbeat od Leadera
        if pkg.term >= self.current_term:
            self.state = NodeState.FOLLOWER
            self.leader_id = pkg.src_id
            self.reset_election_timer()
            # self.logger.debug(f"Heartbeat received from Leader {pkg.src_id}")
