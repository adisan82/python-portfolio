# -*- coding: utf-8 -*-
"""
hyperion_stream.storage.engine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Główny Silnik Składowania (Storage Engine).
Integruje strukturę In-Memory z trwałością WAL (Write-Ahead-Log).

Kluczowe Koncepcje Architektoniczne:
    1. Lock Striping (Sharding): 
       Zamiast jednego globalnego locka (Global Mutex), który zabija wydajność przy wielu rdzeniach/klientach,
       przestrzeń kluczy jest dzielona na N Shardów. Każdy Shard ma własny `asyncio.Lock`.
       To pozwala na równoległe przetwarzanie zapytań do różnych kluczy.
    
    2. Durability Pipeline:
       Request -> WAL Append (Disk) -> Memory Update (RAM).
       Zapewnia to spójność crash-safe. Jeśli padnie prąd po WAL Append, przy restarcie odtworzymy stan pamięci.

    3. Weak References:
       Dla keszowania obiektów, które mogą być zwolnione przez GC, jeśli brakuje pamięci.
       (Tu: Zaimplementowane proste strict-references, weakrefy jako opcja rozszerzenia).
"""

import asyncio
import logging
import zlib
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import dataclass

from .wal import WalManager
from ..core.protocol import LogEntryMeta
from ..core.exceptions import StorageError

logger = logging.getLogger("hyperion.engine")

@dataclass
class EngineMetrics:
    """Kontener na metryki telemetryczne silnika."""
    ops_write: int = 0
    ops_read: int = 0
    bytes_written: int = 0
    wal_flushes: int = 0
    last_snapshot: float = 0.0

class Shard:
    """
    Atomowa jednostka izolacji danych.
    Posiada własny słownik oraz blokadę asynchroniczną.
    """
    __slots__ = ('id', 'data', 'lock', 'stats_keys_count')
    
    def __init__(self, shard_id: int):
        self.id = shard_id
        self.data: Dict[str, bytes] = {}
        # Lock chroni integralności słownika podczas operacji read/write
        self.lock = asyncio.Lock()
        self.stats_keys_count = 0
        
    async def put(self, key: str, value: bytes):
        async with self.lock:
            # Update in-place
            if key not in self.data:
                self.stats_keys_count += 1
            self.data[key] = value

    async def get(self, key: str) -> Optional[bytes]:
        async with self.lock:
            return self.data.get(key)
    
    async def size(self) -> int:
        return len(self.data)


class HyperionEngine:
    """
    Fasada całego systemu storage.
    Odpowiada za routing kluczy do shardów i koordynację WAL.
    """
    
    def __init__(self, data_dir: str, num_shards: int = 64):
        """
        Inicjalizacja silnika.
        
        Args:
            data_dir (str): Ścieżka do katalogu z danymi.
            num_shards (int): Poziom równoległości (potęga 2 zalecana dla szybkiego modulo maską bitową, 
                              ale tu używamy % dla czytelności).
        """
        self.num_shards = num_shards
        logger.info(f"Inicjalizacja silnika z {num_shards} shardami pamięci.")
        
        # Tworzenie shardów
        self.shards = [Shard(i) for i in range(num_shards)]
        
        # Podsystem WAL
        self.wal = WalManager(data_dir)
        
        # Globalny licznik sekwencyjny (Sequence ID generator)
        # W systemie rozproszonym użylibyśmy Snowflake ID lub Vector Clock.
        # W single-node monotoniczny int jest OK.
        self.sequence_id = 0
        
        self.metrics = EngineMetrics()
        self._bg_tasks = []

    def _get_shard(self, key: str) -> Shard:
        """
        Routing logic (Consistent Hashing lub Modulo).
        Używamy CRC32 bo jest szybki i daje niezły rozkład (uniform distribution).
        """
        h = zlib.crc32(key.encode('utf-8'))
        return self.shards[h % self.num_shards]

    async def start(self):
        """Uruchamia procesy tła (Housekeeping)."""
        logger.info("Hyperion Engine: Startowanie...")
        
        # Replay WAL (Odtwarzanie stanu po awarii)
        # TODO: Zaimplementować pełny skan segmentów w poszukiwaniu rekordów
        # Na razie startujemy na czysto (Cold Start).
        
        # Uruchomienie demona msync
        self._bg_tasks.append(asyncio.create_task(self.wal.flush_daemon()))

    async def stop(self):
        """Graceful shutdown - zapewnia spójność danych."""
        logger.info("Zatrzymywanie silnika...")
        for task in self._bg_tasks:
            task.cancel()
        
        # Wymuszony flush ostatniego segmentu
        if self.wal.current_segment:
            self.wal.current_segment.sync()

    async def write(self, key: str, value: bytes) -> int:
        """
        Zapis danych z gwarancją trwałości.
        
        Flow:
        1. Prepare LogEntry (Timestamp, SeqID)
        2. WAL Append (IO Disk)
        3. Memory Put (RAM)
        """
        start_time = time.time()
        self.sequence_id += 1
        
        # 1. Przygotowanie metadanych
        # Obliczamy CRC32 payloadu dla weryfikacji przy odczycie/replayu
        payload_crc = zlib.crc32(value)
        
        entry = LogEntryMeta(
            timestamp=start_time,
            seq_id=self.sequence_id,
            partition_id=0, # Placeholder pod przyszłe funkcje partycjonowania
            crc32=payload_crc
        )
        
        # 2. Zapis do WAL (Mmap copy)
        # To jest potencjalny bottleneck dyskowy.
        self.wal.write_entry(entry, value)
        
        # 3. Aktualizacja stanu pamięci RAM
        shard = self._get_shard(key)
        await shard.put(key, value)
        
        # Telemetria
        self.metrics.ops_write += 1
        self.metrics.bytes_written += len(value)
        
        return self.sequence_id

    async def read(self, key: str) -> Optional[bytes]:
        """Szybki odczyt z RAM (Non-blocking usually)."""
        shard = self._get_shard(key)
        val = await shard.get(key)
        self.metrics.ops_read += 1
        return val

    def get_metrics_report(self) -> str:
        """Generuje raport tekstowy o stanie silnika."""
        return (f"--- Engine Stats ---\n"
                f"Writes: {self.metrics.ops_write}\n"
                f"Reads:  {self.metrics.ops_read}\n"
                f"Bytes:  {self.metrics.bytes_written / 1024 / 1024:.2f} MB\n"
                f"SeqID:  {self.sequence_id}")
