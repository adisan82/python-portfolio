# -*- coding: utf-8 -*-
"""
helix.rpc
~~~~~~~~~

Protokół binarny RPC dla systemu Helix.
Zoptymalizowany pod kątem minimalnego narzutu sieciowego (UDP friendly).

Packet Format:
    [Magic:2] [Type:1] [Term:8] [SrcID:4] [Len:4] [Payload:...]

Magic: 0xHX (Helix)
Types:
    0x01: VOTE_REQ
    0x02: VOTE_RESP
    0x03: APPEND_REQ (Heartbeat/Data)
    0x04: APPEND_RESP
"""

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

class MessageType(IntEnum):
    VOTE_REQ = 1
    VOTE_RESP = 2
    APPEND_REQ = 3
    APPEND_RESP = 4

@dataclass
class Packet:
    msg_type: MessageType
    term: int
    src_id: int
    payload: bytes = b""

    # Format nagłówka: Magic(2s) + Type(B) + Term(Q - unsigned long long) + SrcID(I) + Len(I)
    # Rozmiar: 2 + 1 + 8 + 4 + 4 = 19 bytes
    HEADER_FMT = "!2sBQI I"
    MAGIC = b"HX"

    def pack(self) -> bytes:
        """Serializacja do formatu binarnego."""
        header = struct.pack(
            self.HEADER_FMT,
            self.MAGIC,
            self.msg_type.value,
            self.term,
            self.src_id,
            len(self.payload)
        )
        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> Optional['Packet']:
        """Deserializacja bajtów. Zwraca None w przypadku błędu formatu."""
        header_size = struct.calcsize(cls.HEADER_FMT)
        
        if len(data) < header_size:
            return None
        
        magic, mtype, term, src_id, length = struct.unpack(cls.HEADER_FMT, data[:header_size])
        
        if magic != cls.MAGIC:
            return None
            
        if len(data) < header_size + length:
            # Niepełny pakiet (fragmentacja?)
            return None
            
        payload = data[header_size : header_size + length]
        
        try:
            return cls(MessageType(mtype), term, src_id, payload)
        except ValueError:
            return None # Nieznany typ wiadomości
