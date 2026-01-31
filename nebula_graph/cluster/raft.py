# -*- coding: utf-8 -*-
"""
nebula_graph.cluster.raft
~~~~~~~~~~~~~~~~~~~~~~~~~

Implementacja algorytmu konsensusu RAFT.
Zarządza spójnością klastra rozproszonego.

Role Węzła (Node Roles):
    - FOLLOWER: Pasywny, odbiera logi od Leadera.
    - CANDIDATE: Aktywny podczas wyborów (Election).
    - LEADER: Zarządza klastrem, replikuje logi.

Timery:
    - Election Timeout: Losowy (150-300ms) aby uniknąć split-vote.
    - Heartbeat Interval: Częsty (50ms) aby utrzymać władzę.
"""

import asyncio
import time
import random
import logging
from enum import Enum, auto
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger("nebula.raft")

class RaftState(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

@dataclass
class RaftMessage:
    term: int
    src_id: str
    msg_type: str # 'VOTE_REQ', 'VOTE_RESP', 'APPEND_REQ', 'APPEND_RESP'
    # W prawdziwej implementacji tu byłyby log entries

class RaftNode:
    """
    Maszyna stanów Raft (State Machine).
    Działa w pętli asyncio.
    """
    
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        
        # Persistent state
        self.current_term = 0
        self.voted_for = None
        self.log = []
        
        # Volatile state
        self.state = RaftState.FOLLOWER
        self.leader_id = None
        self.last_heartbeat = time.time()
        
        # Timers configuration
        self.election_timeout_min = 0.150
        self.election_timeout_max = 0.300
        self._reset_election_timer()
        
        self._stop_event = asyncio.Event()

    def _reset_election_timer(self):
        self.election_deadline = time.time() + random.uniform(
            self.election_timeout_min, self.election_timeout_max
        )

    async def start(self):
        """Uruchamia pętlę główną węzła."""
        logger.info(f"Raft Node {self.node_id} starting as FOLLOWER.")
        asyncio.create_task(self._main_loop())

    async def _main_loop(self):
        while not self._stop_event.is_set():
            now = time.time()
            
            if self.state == RaftState.FOLLOWER:
                if now > self.election_deadline:
                    logger.warning("Election timeout! Switching to CANDIDATE.")
                    await self._become_candidate()
            
            elif self.state == RaftState.LEADER:
                # Wyślij heartbeaty
                await self._broadcast_heartbeat()
                await asyncio.sleep(0.05) # 50ms heartbeat interval
            
            await asyncio.sleep(0.01)

    async def _become_candidate(self):
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id # Głosuję na siebie
        self.votes_received = 1
        self._reset_election_timer()
        
        logger.info(f"Starting execution term {self.current_term}. Seeking votes...")
        
        # Mocking vote request (w realu: sieciowe RPC)
        # Tu upraszczamy - zakładamy że dostajemy głosy
        # Simulate network latency
        await asyncio.sleep(0.02)
        
        # Self-promotion logic (uproszczona)
        if len(self.peers) == 0:
            await self._become_leader()

    async def _become_leader(self):
        if self.state != RaftState.CANDIDATE:
            return
            
        self.state = RaftState.LEADER
        self.leader_id = self.node_id
        logger.critical(f"Node {self.node_id} became LEADER for term {self.current_term}!")
        
        # Initial heartbeat
        await self._broadcast_heartbeat()

    async def _broadcast_heartbeat(self):
        # Tutaj normalnie byłaby wysyłka pakietów UDP/TCP do peerów
        # logger.debug(f"Sending PING to {self.peers}")
        pass

    def on_message(self, msg: RaftMessage):
        """Callback wejściowy pakietów sieciowych."""
        if msg.term > self.current_term:
            self.current_term = msg.term
            self.state = RaftState.FOLLOWER
            self.voted_for = None
            self.leader_id = None
            logger.info(f"Stepped down to FOLLOWER (Term {msg.term} seen)")

        if msg.msg_type == 'APPEND_REQ':
            self.last_heartbeat = time.time()
            self._reset_election_timer()
            self.leader_id = msg.src_id
