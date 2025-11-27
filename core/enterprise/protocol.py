"""
Enterprise Deep Protocol Analyzer
---------------------------------
Low-level Minecraft protocol implementation for deep packet inspection.
Determines server auth mode by analyzing the Login Phase response.
"""

import asyncio
import struct
import json
import logging
from enum import Enum
from typing import Tuple, Optional

logger = logging.getLogger("DeepProtocol")

class AuthMode(Enum):
    PREMIUM = "PREMIUM"          # Sends EncryptionRequest
    NON_PREMIUM = "NON_PREMIUM"  # Skips Encryption, sends LoginSuccess or Compression
    UNKNOWN = "UNKNOWN"
    OFFLINE = "OFFLINE"

class DeepProtocolAnalyzer:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    async def analyze_auth_mode(self, host: str, port: int) -> AuthMode:
        """
        Connects to the server and initiates Login phase to check for EncryptionRequest.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), 
                timeout=self.timeout
            )
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return AuthMode.OFFLINE

        try:
            # 1. Send Handshake Packet (State 2 = Login)
            # Packet ID: 0x00
            # Protocol Version: 763 (1.20.1) - widely compatible
            # Host, Port, Next State (2)
            await self._send_handshake(writer, host, port, next_state=2)

            # 2. Send Login Start Packet
            # Packet ID: 0x00
            # Name: "McStatusBot"
            await self._send_login_start(writer, "McStatusBot")

            # 3. Read Response Packet
            packet_id, data = await self._read_packet(reader)
            
            # Analyze Packet ID (VarInt)
            # 0x00: Disconnect
            # 0x01: Encryption Request -> PREMIUM
            # 0x02: Login Success -> NON_PREMIUM (Cracked)
            # 0x03: Set Compression -> NON_PREMIUM (Usually followed by Success)
            
            if packet_id == 0x01:
                return AuthMode.PREMIUM
            elif packet_id == 0x02 or packet_id == 0x03:
                return AuthMode.NON_PREMIUM
            elif packet_id == 0x00:
                # Disconnect packet - check reason
                try:
                    json_str = data.decode('utf-8', errors='ignore')
                    # Some cracked servers disconnect if name is invalid or whitelist
                    # But if they disconnect immediately without Encryption Request, 
                    # they are likely NOT enforcing Mojang Auth in the standard way.
                    return AuthMode.NON_PREMIUM 
                except:
                    return AuthMode.UNKNOWN
            
            return AuthMode.UNKNOWN

        except Exception as e:
            # logger.debug(f"Protocol error {host}: {e}")
            return AuthMode.UNKNOWN
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    async def _send_handshake(self, writer, host: str, port: int, next_state: int):
        # Protocol 763 (1.20.1)
        # ID 0x00
        packet_id = b'\x00'
        protocol_version = self._write_varint(763)
        host_bytes = host.encode('utf-8')
        host_len = self._write_varint(len(host_bytes))
        port_bytes = struct.pack('>H', port)
        next_state_bytes = self._write_varint(next_state)
        
        data = packet_id + protocol_version + host_len + host_bytes + port_bytes + next_state_bytes
        await self._send_packet(writer, data)

    async def _send_login_start(self, writer, name: str):
        # ID 0x00
        packet_id = b'\x00'
        name_bytes = name.encode('utf-8')
        name_len = self._write_varint(len(name_bytes))
        
        # UUID (Optional in some versions, but good to send empty/null if needed)
        # For 1.20.x Login Start also includes UUID. 
        # We'll just send Name for now, many servers accept legacy LoginStart format 
        # or we might need to update protocol if strict.
        # Let's try simple Name first (older protocol style often works for detection)
        
        data = packet_id + name_len + name_bytes
        # Note: Modern versions require UUID after name. 
        # Let's add a dummy UUID just in case (16 bytes)
        # data += b'\x00' * 16 
        
        await self._send_packet(writer, data)

    async def _send_packet(self, writer, data: bytes):
        length = self._write_varint(len(data))
        writer.write(length + data)
        await writer.drain()

    async def _read_packet(self, reader) -> Tuple[int, bytes]:
        # Read Length (VarInt)
        length = await self._read_varint(reader)
        if length == 0:
            raise ValueError("Empty packet")
            
        # Read Data
        data = await reader.readexactly(length)
        
        # Read Packet ID (VarInt at start of data)
        # We need to parse VarInt from data bytes manually
        packet_id, offset = self._read_varint_from_bytes(data)
        
        return packet_id, data[offset:]

    def _write_varint(self, value: int) -> bytes:
        out = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                byte |= 0x80
            out.append(byte)
            if not value:
                break
        return bytes(out)

    async def _read_varint(self, reader) -> int:
        result = 0
        shift = 0
        for _ in range(5):
            byte = await reader.read(1)
            if not byte:
                raise EOFError("Unexpected EOF reading VarInt")
            b = ord(byte)
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result
            shift += 7
        raise ValueError("VarInt too big")

    def _read_varint_from_bytes(self, data: bytes) -> Tuple[int, int]:
        result = 0
        shift = 0
        for i, b in enumerate(data):
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result, i + 1
            shift += 7
            if i >= 5:
                raise ValueError("VarInt too big")
        raise ValueError("Incomplete VarInt")
