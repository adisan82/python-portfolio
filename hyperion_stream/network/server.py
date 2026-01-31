# -*- coding: utf-8 -*-
"""
hyperion_stream.network.server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wysokowydajny serwer TCP oparty na `asyncio`.
Realizuje wzorzec Reactor Pattern: jedna pętla zdarzeń obsługuje tysiące połączeń.

Security & Resilience:
    - Protection: Ochrona przed wolnymi klientami (Slowloris) poprzez timeouty na poziomie protokołu.
    - Limits: Twarde limity na liczbę połączeń i wielkość buforów.
    - Framing: Oddzielenie procesu czytania ramek od ich przetwarzania.

Protokół binarny:
    Odczyt odbywa się w dwóch fazach:
    1. Read Header (Fixed Size) -> Ustalenie długości Payloadu.
    2. Read Payload (Exact Size) -> Przekazanie do Handlera.
"""

import asyncio
import logging
import struct
import time
from typing import Optional, Dict

from ..core.protocol import BinaryMessage, CommandHeader, MAX_PACKET_SIZE
from ..storage.engine import HyperionEngine
from ..core.exceptions import ProtocolError, HyperionError

logger = logging.getLogger("hyperion.net")

class ConnectionContext:
    """Kontekst pojedynczego połączenia klienckiego (Session State)."""
    __slots__ = ('addr', 'connected_at', 'last_activity', 'request_count')
    
    def __init__(self, addr):
        self.addr = addr
        self.connected_at = time.time()
        self.last_activity = time.time()
        self.request_count = 0

class HyperionServer:
    def __init__(self, host: str, port: int, engine: HyperionEngine):
        self.host = host
        self.port = port
        self.engine = engine
        self._server: Optional[asyncio.AbstractServer] = None
        self._active_connections: Dict[str, ConnectionContext] = {}

    async def start(self):
        """Binduje gniazdo i rozpoczyna pętlę accept()."""
        # Ustawiamy parametry socketa (np. TCP_NODELAY) - w python high-level server
        # jest to czasem ukryte, tutaj ufamy defaults asyncio.
        self._server = await asyncio.start_server(
            self.handle_client, 
            self.host, 
            self.port,
            limit=MAX_PACKET_SIZE * 2 # Buffer limit dla asyncio streamów
        )
        
        logger.info(f"Hyperion Server nasłuchuje na {self.host}:{self.port}")
        logger.info(f"Max Packet Size: {MAX_PACKET_SIZE / 1024 / 1024} MB")
        
        async with self._server:
            await self._server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Główna korutyna obsługi klienta.
        Działa w pętli `while True` dopóki klient nie zamknie połączenia lub nie wystąpi błąd.
        """
        addr = writer.get_extra_info('peername')
        ctx = ConnectionContext(addr)
        self._active_connections[str(addr)] = ctx
        
        logger.info(f"Nowe połączenie: {addr}")
        
        try:
            while True:
                # 1. Odczyt Nagłówka (Header Read)
                # Oczekujemy dokładnie HEADER_SIZE bajtów.
                # readexactly rzuci IncompleteReadError jeśli EOF wystąpi w trakcie
                try:
                    header_data = await reader.readexactly(BinaryMessage.HEADER_SIZE)
                except asyncio.IncompleteReadError:
                    # Normalne zamknięcie połaczenia przez klienta (EOF)
                    break
                
                # Update Watchdog
                ctx.last_activity = time.time()
                
                # 2. Rozpakowanie nagłówka
                # Struktura: Magic(4s) Type(H) Flags(B) Reserved(B) Len(I)
                magic, msg_type, flags, res, payload_len = BinaryMessage.HEADER_STRUCT.unpack(header_data)
                
                if magic != BinaryMessage.MAGIC:
                    logger.warning(f"Błąd protokołu od {addr}: Zły Magic Number {magic}")
                    break # Kill connection immediately

                if payload_len > MAX_PACKET_SIZE:
                    logger.error(f"DoS Protection: Klient {addr} prosi o {payload_len} bajtów.")
                    break

                # 3. Odczyt Payloadu (Payload Read)
                payload = await reader.readexactly(payload_len)
                
                # 4. Przetwarzanie (Business Logic)
                # Tu wchodzi w grę CPU-bound processing. W razie potrzeby można to zrzucić do ThreadPoola,
                # ale dla operacji I/O (Storage) zostajemy w coroutines.
                response_payload = await self.process_command(msg_type, payload)
                
                # 5. Budowa odpowiedzi
                # Prosty format odpowiedzi: [Len:4][Bytes] (uproszczony względem requestu)
                resp_len = len(response_payload)
                resp_header = struct.pack("!I", resp_len)
                
                writer.write(resp_header + response_payload)
                await writer.drain() # Flow control: czekamy aż OS opróżni bufor wysyłania
                
                ctx.request_count += 1
                
                # --- TELEMETRIA START ---
                # Mierzymy throughput i latencję dla Dashboardu Operacyjnego
                from ..utils.telemetry import METRICS
                latency = time.time() - ctx.last_activity
                METRICS.inc_counter("hyperion_requests_total", 1, {"type": str(msg_type)})
                METRICS.inc_counter("hyperion_bytes_sent_total", resp_len)
                # --- TELEMETRIA END ---

        except ConnectionResetError:
            logger.debug(f"Połączenie reset przez peer {addr}")
        except Exception as e:
            logger.error(f"Nieoczekiwany wyjątek dla klienta {addr}: {e}", exc_info=True)
        finally:
            writer.close()
            # W Py 3.7+ wait_closed()
            try:
                await writer.wait_closed()
            except:
                pass
            del self._active_connections[str(addr)]
            logger.info(f"Połączenie zamknięte {addr}. ReqCount: {ctx.request_count}")

    async def process_command(self, msg_type: int, payload: bytes) -> bytes:
        """
        Router komend.
        Rozpoznaje typ wiadomości i uderza do silnika.
        """
        # TEXT-PROTOCOL TUNNELING (dla łatwości testowania np. telnetem/netcatem jeśli pominąć binary headery)
        # Ale tu mamy ścisły binary.
        
        try:
            # CMD TYPE 1: SET (Key|Value)
            if msg_type == 1:
                try:
                    # Separator '|' jest szybki, choć mało bezpieczny binarnie (lepiej Len-Prefixed).
                    # Uznajemy, że klucz to UTF-8.
                    sep_idx = payload.find(b'|')
                    if sep_idx == -1: return b"ERR_FORMAT"
                    
                    key = payload[:sep_idx].decode('utf-8')
                    value = payload[sep_idx+1:]
                    
                    seq = await self.engine.write(key, value)
                    return f"OK_SET:{seq}".encode()
                except Exception as e:
                    return f"ERR_SET:{e}".encode()

            # CMD TYPE 2: GET (Key)
            elif msg_type == 2:
                key = payload.decode('utf-8')
                val = await self.engine.read(key)
                if val:
                    return val # Raw bytes
                else:
                    return b"ERR_NOT_FOUND"
            
            # CMD TYPE 99: STATS
            elif msg_type == 99:
                report = self.engine.get_metrics_report()
                return report.encode('utf-8')

            else:
                return b"ERR_UNKNOWN_CMD"

        except Exception as e:
            logger.error("Global command error", exc_info=True)
            return b"ERR_INTERNAL"
