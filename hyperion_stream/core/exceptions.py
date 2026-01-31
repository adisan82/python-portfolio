# -*- coding: utf-8 -*-
"""
hyperion_stream.core.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Centralna hierarchia wyjątków dla silnika Hyperion Stream.
Unikamy generycznych wyjątków; łapanie specyficznych błędów pozwala na granularne strategie odzyskiwania (recovery)
w maszynie stanów fault-tolerant.

Każdy wyjątek dziedziczy po `HyperionError`, co pozwala na globalne łapanie błędów systemowych na poziomie Workera.
"""

class HyperionError(Exception):
    """Bazowy, abstrakcyjny wyjątek dla całego systemu Hyperion."""
    pass


class ProtocolError(HyperionError):
    """
    Krytyczny błąd warstwy protokołu.
    Rzucany, gdy parsowanie binarne napotka niezgodność (zły Magic Number, nieznana wersja protokołu, błędy ramek).
    Zazwyczaj skutkuje natychmiastowym zerwaniem połączenia TCP, aby uniknąć zatrucia bufora (poison packaging).
    """
    pass


class PacketSizeExceededError(ProtocolError):
    """
    Rzucany, gdy zadeklarowana długość Payloadu w nagłówku przekracza `MAX_PACKET_SIZE`.
    Ochrona przed atakami DoS (Allocation Flooding).
    """
    pass


class ChecksumError(ProtocolError):
    """
    Krytyczny błąd integralności danych (Data Integrity Violation).
    Rzucany, gdy weryfikacja sumy kontrolnej CRC32 entry logu lub pakietu sieciowego nie powiedzie się.
    W kontekście WAL oznacza to zazwyczaj uszkodzenie dysku (bit rot) lub przerwany zapis (torn write).
    Wymaga uruchomienia procedury `wal_recovery`.
    """
    pass


class StorageError(HyperionError):
    """Bazowy błąd dla operacji I/O, mmap i persystencji."""
    pass


class WalCorruptionError(StorageError):
    """
    Rzucany podczas inicjalizacji silnika, gdy struktura WAL (Write-Ahead-Log) jest niespójna.
    Może wymagać manualnej interwencji (narzędzie `hyperion-chk`) lub automatycznego ucięcia (truncation) do ostatniego poprawnego offsetu.
    """
    pass


class WalSegmentFullError(StorageError):
    """
    Sygnalizuje, że bieżący segment pamięci mapowanej (mmap) jest pełny.
    Wymusza na silniku rotację segmentu (rollover) i fsync starego pliku.
    """
    pass


class ShardLockedError(StorageError):
    """
    Rzucany przy próbie dostępu do Shardu, który jest w trakcie snapshotowania lub kompaktowania (compaction).
    Klient powinien ponowić próbę (retry with backoff).
    """
    pass


class BackpressureException(HyperionError):
    """
    Wyjątek kontroli przepływu (Flow Control).
    Rzucany, gdy wewnętrzne kolejki (ingress/processing) przekraczają High-Water Mark.
    Warstwa sieciowa (TCP Reactor) powinna przestać czytać z socketów (`transport.pause_reading()`), 
    aż ciśnienie spadnie poniżej Low-Water Mark.
    """
    pass
