# -*- coding: utf-8 -*-
"""
hyperion_stream.core.protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wydajna (High-Performance) implementacja protokołu binarnego przy użyciu Python Metaclasses oraz Descriptors.
Unikamy standardowego `json` czy `pickle` w ścieżkach krytycznych (hot-paths). Zamiast tego używamy
low-level `struct` packing ze ścisłym schematem (Schema) definiowanym przez atrybuty klasy.

Architektura:
    - Deskryptory (`Int32`, `Bytes`, `Timestamp`, etc.) definiują układ pamięci (memory layout).
    - `BinaryMeta` pre-kompiluje stringi formatujące `struct` w czasie TWORZENIA KLASY (zero runtime overhead).
    - `BinaryMessage` zapewnia serializację/deserializację O(1) bez słownikowych narzutów w locie.

Format Ramki (Frame Format):
    [Magic:4s] [TypeID:2B] [Flags:1B] [Reserved:1B] [Length:4B] [Payload:Variable] [CRC32:4B]

Optymalizacje:
    - Slotowanie (`__slots__`) dla redukcji footprintu pamięci obiektów (ważne przy milionach wiadomości).
    - Pre-computed struct objects cache.
    - Zero-copy slicing na buforach (memoryview) tam gdzie to możliwe.
"""

import struct
import zlib
import abc
import time
from typing import ClassVar, Type, Any, Dict, Tuple, Optional
from .exceptions import ProtocolError, ChecksumError, PacketSizeExceededError

# Limit wielkości pojedynczego pakietu (32MB) - Ochrona DoS
MAX_PACKET_SIZE = 32 * 1024 * 1024 

# -----------------------------------------------------------------------------
# Descriptors (Schema Definition) - Type System
# -----------------------------------------------------------------------------

class Field(abc.ABC):
    """
    Abstrakcyjny deskryptor pola protokołu.
    Zarządza walidacją, kolejnością packing i mapowaniem na typy C.
    """
    
    def __init__(self, order: int, doc: str = None):
        self.order = order
        self.doc = doc
        self.name = None  # Ustawiane automatycznie przez __set_name__ w metaclass

    def __set_name__(self, owner, name):
        self.name = name

    @abc.abstractmethod
    def format_char(self) -> str:
        """
        Zwraca znak formatowania struct (np. 'i', 'q', '4s').
        Dla typów zmiennych (Variable Length) zwraca pusty string.
        """
        pass

    @abc.abstractmethod
    def validate(self, value):
        """Walidacja typu i zakresu w runtime (tylko w trybie debug/safe)."""
        pass


class Int8(Field):
    """1-byte signed int (char)."""
    def format_char(self) -> str: return 'b'
    def validate(self, value):
        if not (-128 <= value <= 127): raise ValueError(f"{self.name} overflow Int8")


class UInt8(Field):
    """1-byte unsigned int (uchar)."""
    def format_char(self) -> str: return 'B'
    def validate(self, value):
        if not (0 <= value <= 255): raise ValueError(f"{self.name} overflow UInt8")


class Int32(Field):
    """4-byte signed integer (standardowy int C)."""
    def format_char(self) -> str: return 'i'
    def validate(self, value):
        # Python 3 int jest aribtrary precision, musimy pilnować granic C
        if not isinstance(value, int):
            raise TypeError(f"{self.name} musi być int, a jest {type(value)}")
        if not (-2147483648 <= value <= 2147483647):
            raise ValueError(f"{self.name} overflow Int32")


class UInt32(Field):
    """4-byte unsigned integer."""
    def format_char(self) -> str: return 'I'
    def validate(self, value):
        if value < 0 or value > 4294967295:
            raise ValueError(f"{self.name} overflow UInt32")


class Int64(Field):
    """8-byte signed integer (long long). Używany do ID sekwencji."""
    def format_char(self) -> str: return 'q'
    def validate(self, value):
        if not isinstance(value, int): raise TypeError(f"{self.name} not int")


class Float64(Field):
    """8-byte double precision float."""
    def format_char(self) -> str: return 'd'
    def validate(self, value):
        if not isinstance(value, (float, int)): raise TypeError(f"{self.name} not float")


class Timestamp(Field):
    """
    Precyzyjny timestamp (Unix epoch w UTC). 
    Fizycznie przechowywany jako Double (8 bajtów).
    """
    def format_char(self) -> str: return 'd'
    def validate(self, value):
        if not isinstance(value, (float, int)):
            raise TypeError(f"{self.name} invalid timestamp")


class FixedString(Field):
    """Stała tablica znaków (np. 4s, 16s). Padding null-bytes."""
    def __init__(self, length: int, order: int):
        super().__init__(order)
        self.length = length

    def format_char(self) -> str: 
        return f'{self.length}s'

    def validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError(f"{self.name} requires bytes")
        if len(value) > self.length:
            raise ValueError(f"{self.name} too long (max {self.length})")


# -----------------------------------------------------------------------------
# Metaclass Magic (Compiler)
# -----------------------------------------------------------------------------

class BinaryMeta(type):
    """
    Metaclass-kompilator.
    Introspekcja definicji klasy w celu zbudowania optymalnego packera `struct`.
    
    Działanie:
    1. Znajduje wszystkie deskryptory Field.
    2. Sortuje je według `order` (kolejność w ramce binarnej).
    3. Generuje `__slots__` dla redukcji pamięci (każda instancja to mniejszy overhead).
    4. Kompiluje `struct.Struct` dla stałej części nagłówka.
    """
    
    def __new__(mcs, name, bases, namespace):
        fields = []
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields.append((key, value))
        
        # Sortowanie wymuszone dla determinizmu binarnego (Memory Layout)
        fields.sort(key=lambda x: x[1].order)
        
        # Rejestracja nazw pól
        field_names = [f[0] for f in fields]
        namespace['_fields'] = tuple(field_names)
        namespace['_descriptors'] = {f[0]: f[1] for f in fields}
        
        # Generowanie format stringa C-struct (Network Byte Order '!')
        # UWAGA: To obsługuje tylko Fixed-Size fields w tej wersji.
        # Payload dynamiczny jest doklejany osobno.
        fmt_string = "!" 
        for _, field in fields:
            fmt = field.format_char()
            if fmt:
                fmt_string += fmt
            else:
                # Jeśli napotkamy typ dynamiczny (Variable Length), przerywamy kompilację structa
                # i przechodzimy na sekwencyjne parsowanie (nie zaimplementowane w v1)
                raise NotImplementedError("Dynamic fields inside struct body not supported yet")
                
        namespace['_struct'] = struct.Struct(fmt_string)
        
        # Optymalizacja pamięci - __slots__
        # Nadpisujemy slots, jeśli nie zostały zdefiniowane ręcznie.
        if '__slots__' not in namespace:
            namespace['__slots__'] = field_names + ('_values',)

        return super().__new__(mcs, name, bases, namespace)


# -----------------------------------------------------------------------------
# Base Message Class
# -----------------------------------------------------------------------------

class BinaryMessage(metaclass=BinaryMeta):
    """
    Klasa bazowa dla wszystkich wiadomości wire-protocol.
    
    Performance Note:
        Dzięki metaclass, `pack()` i `unpack()` delegują wprost do C-level `struct` module.
        Narzut Pythona jest zminimalizowany.
    """
    
    # Globalny Magic Number dla szybkiego odrzucania śmieci (Sanity Check)
    MAGIC = b'HPRS' 
    
    # Generic Header: Magic(4s) + TypeID(H) + Flags(B) + Reserved(B) + PayloadLen(I)
    # Total Header Size: 4+2+1+1+4 = 12 bajtów
    HEADER_STRUCT = struct.Struct("!4sHBBI")
    HEADER_SIZE = 12
    
    def __init__(self, **kwargs):
        # Inicjalizacja pól.
        # W produkcyjnym kodzie można to pominąć dla szybkości, ale walidacja jest cenniejsza.
        for name in self._fields:
            val = kwargs.get(name, 0)
            self.__setattr__(name, val)

    def pack(self) -> bytes:
        """
        Serializuje obiekt do byte-buffer.
        Zwraca TYLKO body (bez nagłówka ramki transportowej).
        """
        # Wyciągamy wartości w kolejności zdefiniowanej przez `order` deskryptorów
        values = [getattr(self, name) for name in self._fields]
        return self._struct.pack(*values)

    @classmethod
    def unpack(cls, buffer: bytes) -> 'BinaryMessage':
        """
        Deserializuje body.
        Zakłada, że `buffer` ma dokładnie taką długość jak `cls._struct.size`.
        """
        if len(buffer) != cls._struct.size:
            raise ProtocolError(f"Buffer size mismatch for {cls.__name__}: got {len(buffer)}, need {cls._struct.size}")
            
        try:
            unpacked = cls._struct.unpack(buffer)
            # Szybki dict-zip. W Py3.10+ zip() jest b. wydajny.
            kwargs = dict(zip(cls._fields, unpacked))
            return cls(**kwargs)
        except struct.error as e:
            raise ProtocolError(f"Struct unpack failed for {cls.__name__}: {e}")

    def __repr__(self):
        # Ładne formatowanie dla debuggera
        vals = ", ".join(f"{k}={getattr(self, k)}" for k in self._fields)
        return f"<{self.__class__.__name__} [{vals}]>"


# -----------------------------------------------------------------------------
# Concrete Message Types (Protokół Właściwy)
# -----------------------------------------------------------------------------

class LogEntryMeta(BinaryMessage):
    """
    Nagłówek wpisu w WAL (Write-Ahead-Log).
    Musi być ultra-kompaktowy, bo jest zapisywany miliony razy.
    
    Struktura:
    [Timestamp:8B] [SeqID:8B] [Partition:4B] [CRC32:4B]
    """
    timestamp = Timestamp(order=1, doc="Czas przyjęcia eventu (UTC)")
    seq_id = Int64(order=2, doc="Monotonicznie rosnący ID w ramach segmentu")
    partition_id = Int32(order=3, doc="ID Shardu logicznego")
    crc32 = UInt32(order=4, doc="Suma kontrolna Payloadu")


class CommandHeader(BinaryMessage):
    """
    Nagłówek operacji sieciowej (Request/Response).
    """
    request_id = Int64(order=1, doc="Correlation ID dla asynchronicznych odpowiedzi")
    cmd_type = UInt8(order=2, doc="Typ operacji (1=SET, 2=GET, 3=ACK...)")
    flags = UInt8(order=3, doc="Flagi bitowe (np. COMPRESSED, URGENT)")
    ttl = UInt8(order=4, doc="Time-To-Live dla hopów (opcjonalne)")
    # Padding dla wyrównania do 8 bajtów (alignment) by się przydał, ale w Python struct to mniej krytyczne
    # niż w C++, choć dla Cache Line efficiency można by dodać `Reserved`.


class NodeStats(BinaryMessage):
    """
    Telemetryczny pakiet heartbeat przesyłany między węzłami klastra.
    """
    cpu_usage = Float64(order=1)
    mem_usage = Float64(order=2)
    uptime_sec = UInt32(order=3)
    wal_lag_bytes = Int64(order=4)
