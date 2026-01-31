# -*- coding: utf-8 -*-
"""
hyperion_stream.storage.wal
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementacja Write-Ahead-Log (WAL) zorientowana na wydajność i bezpieczeństwo danych.
Podsystem ten jest sercem trwałości (Durability) bazy.

Architecture Constraints:
    - Append-only: Zapisy są sekwencyjne, co maksymalizuje przepustowość dysku (spinners & SSD).
    - Memory-Mapped Files (mmap): Używamy `mmap` do zarządzania stronicowaniem przez OS. 
      Unikamy podwójnego buforowania (User-Space buffer -> Kernel buffer).
    - Segmented Logs: Dane są dzielone na segmenty (pliki), które są rotowane po osiągnięciu limitu (np. 64MB).
    - Crash Recovery: Przy starcie system skanuje ostatni wrog segment w poszukiwaniu "Torn Writes" (urwanych zapisów).

Synchronizacja:
    - Metoda `append()` nie jest thread-safe (powinna być wołana z jednego wątku/procesu piszącego - Single Writer Principle).
    - `fsync` jest kontrolowany polityką (Every-Write vs Periodic).
"""

import os
import mmap
import struct
import time
import asyncio
import logging
import zlib
from pathlib import Path
from typing import BinaryIO, Optional, List, Tuple

from ..core.protocol import LogEntryMeta, BinaryMessage
from ..core.exceptions import (
    StorageError, WalCorruptionError, ChecksumError, WalSegmentFullError
)

# Logger konfiguracja
logger = logging.getLogger("hyperion.wal")

class WalSegment:
    """
    Fizyczna reprezentacja pliku logu.
    Zarządza mapowaniem pliku w wirtualną przestrzeń adresową procesu.
    
    States:
        - ACTIVE: Plik jest otwarty do zapisu.
        - CLOSED: Plik jest zamknięty (Immutable), gotowy do archiwizacji lub usunięcia.
    """
    
    # Rozmiar segmentu: 64MB. Jest to kompromis między częstotliwością rotacji a fragmentacją.
    SEGMENT_SIZE = 64 * 1024 * 1024 
    
    # Wersja formatu pliku (Magiczna liczba nagłówka segmentu)
    SEGMENT_MAGIC = 0xAABBCCDD
    
    def __init__(self, path: Path, read_only: bool = False, create: bool = False):
        self.path = path
        self.read_only = read_only
        
        self._f: Optional[BinaryIO] = None
        self._mmap: Optional[mmap.mmap] = None
        self._write_cursor = 0
        self._fd = None
        
        if create or path.exists():
            self._open(create_new=create)
        else:
            raise FileNotFoundError(f"Segment {path} not found")

    def _open(self, create_new: bool):
        """
        Low-level inicjalizacja mmap.
        Używa deskryptorów plików OS dla kontroli flag (O_DIRECT potencjalnie w przyszłości).
        """
        flags = os.O_RDWR | os.O_CREAT if not self.read_only else os.O_RDONLY
        
        # Otwieramy deskryptor
        try:
            self._fd = os.open(str(self.path), flags)
        except OSError as e:
            raise StorageError(f"Nie można otworzyć segmentu {self.path}: {e}")

        # Jeśli tworzymy nowy segment, alokujemy miejsce (fallocate/ftruncate)
        if create_new:
            try:
                os.ftruncate(self._fd, self.SEGMENT_SIZE)
            except OSError as e:
                os.close(self._fd)
                raise StorageError(f"Alokacja dyskowa nieudana: {e}")
            
            # Reset kursora zapisu na początek (po nagłówku pliku, jeśli byśmy go mieli)
            self._write_cursor = 0
        else:
            # TRYB RECOVERY / READ
            # Musimy znaleźć koniec danych. W prostej wersji skanujemy, 
            # w wersji PRO mamy zewnętrzny plik 'checkpoint'.
            # Tutaj zakładamy, że menadżer ustawi kursor, lub zaczynamy od 0.
            self._write_cursor = 0 

        # Mapowanie pamięci
        prot = mmap.PROT_READ
        access = mmap.ACCESS_READ
        if not self.read_only:
            prot |= mmap.PROT_WRITE
            access = mmap.ACCESS_WRITE

        try:
            self._mmap = mmap.mmap(self._fd, self.SEGMENT_SIZE, access=access)
        except Exception as e:
            os.close(self._fd)
            raise StorageError(f"mmap failed: {e}")

    def append(self, packet: bytes) -> int:
        """
        Atomowe (w kontekście pythona i GIL) dopisanie danych do bufora pamięci.
        
        Args:
            packet (bytes): Zserializowana struktura meta + payload.
            
        Returns:
            int: Offset startowy zapisanego bloku.
            
        Raises:
            WalSegmentFullError: Gdy brak miejsca.
        """
        size = len(packet)
        # Sprawdzenie granic ('Bound Check')
        if self._write_cursor + size > self.SEGMENT_SIZE:
             raise WalSegmentFullError(f"Segment {self.path.name} pełny ({self._write_cursor}/{self.SEGMENT_SIZE})")
        
        # Kopiowanie pamięci (memcpy)
        # To jest operacja bardzo szybka w Pythonie dla bytes -> mmap slice assignment
        end_pos = self._write_cursor + size
        self._mmap[self._write_cursor : end_pos] = packet
        
        written_at = self._write_cursor
        self._write_cursor += size
        
        return written_at

    def read_at(self, offset: int, size: int) -> bytes:
        """
        Odczyt losowy (Random Access).
        Użyteczne przy replayu lub pobieraniu historycznym.
        """
        if offset + size > self.SEGMENT_SIZE:
            # To może oznaczać korupcję lub błąd logiki
            raise ValueError("Read beyond segment boundary")
        return self._mmap[offset : offset + size]

    def sync(self):
        """
        Wymuszenie zrzutu brudnych stron (Dirty Pages) na dysk fizyczny.
        Odpowiednik `fsync` / `msync`.
        Krytyczne dla gwarancji 'D' w bazie ACID.
        """
        if self._mmap:
            self._mmap.flush()

    def close(self):
        """Zwolnienie zasobów."""
        if self._mmap:
            # Ostatni sync przed zamknięciem
            if not self.read_only:
                self._mmap.flush()
            self._mmap.close()
        if self._fd:
            os.close(self._fd)


class WalManager:
    """
    Zarządca Cyklu Życia WAL (Lifecycle Manager).
    Odpowiada za rotację plików, odzyskiwanie spójności (Recovery) i koordynację I/O.
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_segment: Optional[WalSegment] = None
        self.segments_history: List[Path] = []
        
        # Inicjalizacja: jeśli są pliki, trzeba by zrobić recovery.
        # Na potrzeby startu projektu #1, zawsze startujemy nowym segmentem 
        # (w produkcji szukalibyśmy ostatniego).
        self._rotate_segment()

    def _rotate_segment(self):
        """
        Tworzy nowy segment logu i zamyka stary.
        """
        if self.current_segment:
            logger.info("Zamykanie obecnego segmentu WAL przed rotacją...")
            self.current_segment.sync()
            self.current_segment.close()
            # Tutaj moglibyśmy dodać stary segment do listy readonly history, jeśli byśmy go potrzebowali.
        
        # Nazewnictwo: wal_TIMESTAMP_SEQ.log
        timestamp = int(time.time() * 1000)
        filename = f"wal_{timestamp}.log"
        path = self.data_dir / filename
        
        logger.info(f"Otwieranie nowego segmentu WAL: {filename}")
        self.current_segment = WalSegment(path, create=True)
        self.segments_history.append(path)

    def write_entry(self, entry_meta: LogEntryMeta, payload: bytes) -> int:
        """
        Fasada zapisu. Formatuje pakiet binarny i pcha do segmentu.
        
        Format na dysku:
        [MetaLen:4] [MetaStruct] [PayloadLen:4] [PayloadBytes]
        
        Dla szybkości używamy struct.pack bezpośrednio.
        """
        # 1. Serializacja metadanych
        meta_bytes = entry_meta.pack()
        meta_len = len(meta_bytes)
        payload_len = len(payload)
        
        # 2. Budowa nagłówka Längen-Prefix (Length-Prefix Header)
        # Format: !II (MetaLen, PayloadLen) - 8 bajtów
        headers = struct.pack("!II", meta_len, payload_len)
        
        # 3. Złożenie całego bloku (minimalizujemy liczbę wywołań append)
        # W Pythonie konkatenacja bytes jest szybka dla małych chunków, 
        # ale dla dużych payloadów lepiej byłoby użyć iovecs (writev).
        # mmap wspiera slice assignment, więc jeden duży blob jest OK.
        full_packet = headers + meta_bytes + payload
        
        try:
            return self.current_segment.append(full_packet)
        except WalSegmentFullError:
            logger.warning("Segment WAL pełny. Rotacja...")
            self._rotate_segment()
            # Rekurencja (jednopoziomowa) - próba zapisu do nowego seg
            return self.current_segment.append(full_packet)

    async def flush_daemon(self, interval: float = 0.1):
        """
        Background worker w pętli asyncio.
        Cyklicznie woła msync(), aby zapewnić, że dane nie siedzą tylko w RAMie
        przez zbyt długi czas (Gwarancja: dane tracimy max z ostatnich `interval` sekund).
        """
        logger.info("Startowanie demona persystencji (Flush Daemon).")
        try:
            while True:
                await asyncio.sleep(interval)
                if self.current_segment:
                    # To jest operacja blokująca IO, więc w idealnym świecie Executor
                    # ale msync na mmap jest zazwyczaj szybki jeśli OS robi writeback w tle.
                    self.current_segment.sync()
        except asyncio.CancelledError:
            logger.info("Flush Daemon zatrzymany.")
            # Final sync upon exit
            if self.current_segment:
                self.current_segment.sync()
