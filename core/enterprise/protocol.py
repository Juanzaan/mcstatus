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
import uuid

logger = logging.getLogger("DeepProtocol")

class AuthMode(Enum):
    PREMIUM = "PREMIUM"          # Sends EncryptionRequest
    NON_PREMIUM = "NON_PREMIUM"  # Skips Encryption, sends LoginSuccess or Compression
    UNKNOWN = "UNKNOWN"
    OFFLINE = "OFFLINE"

class DeepProtocolAnalyzer:
    def __init__(self, timeout: float = 10.0):  # Increased from 5.0 to 10.0
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
            
            # Detailed logging for debugging
            print(f"[DEBUG] {host}: Received packet ID=0x{packet_id:02X}, data_len={len(data)}")
            logger.debug(f"Received packet from {host}: ID=0x{packet_id:02X}, data_len={len(data)}")
            
            # Analyze Packet ID (VarInt)
            # 0x00: Disconnect
            # 0x01: Encryption Request -> PREMIUM
            # 0x02: Login Success -> NON_PREMIUM (Cracked)
            # 0x03: Set Compression -> NON_PREMIUM (Usually followed by Success)
            
            if packet_id == 0x01:
                print(f"[DEBUG] {host}: Encryption Request -> PREMIUM")
                logger.debug(f"{host} sent Encryption Request -> PREMIUM")
                return AuthMode.PREMIUM
            elif packet_id == 0x02 or packet_id == 0x03:
                print(f"[DEBUG] {host}: Login Success/Compression -> NON_PREMIUM")
                logger.debug(f"{host} sent Login Success/Compression -> NON_PREMIUM")
                return AuthMode.NON_PREMIUM
            elif packet_id == 0x00:
                # Disconnect packet - log the reason
                try:
                    # Try to parse as JSON (modern format)
                    disconnect_reason = data.decode('utf-8', errors='ignore')
                    print(f"[DEBUG] {host}: Disconnect - {disconnect_reason[:100]}")
                    logger.debug(f"{host} disconnected: {disconnect_reason[:100]}")
                    
                    # Some cracked servers disconnect if name is invalid or whitelist
                    # But if they disconnect immediately without Encryption Request, 
                    # they are likely NOT enforcing Mojang Auth in the standard way.
                    return AuthMode.NON_PREMIUM 
                except Exception as e:
                    print(f"[DEBUG] {host}: Disconnect parse error: {e}")
                    logger.debug(f"{host} disconnect parse error: {e}")
                    return AuthMode.UNKNOWN
            
            print(f"[DEBUG] {host}: Unknown packet ID 0x{packet_id:02X}")
            logger.debug(f"{host} returned unknown packet ID 0x{packet_id:02X}")
            return AuthMode.UNKNOWN

        except Exception as e:
            print(f"[DEBUG] {host}: Protocol error: {e}")
            # logger.debug(f"Protocol error {host}: {e}")
            return AuthMode.UNKNOWN
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    async def _send_handshake(self, writer, host: str, port: int, next_state: int):
        # Protocol 47 (1.8.9) - Most widely compatible
        # Use 1.8.9 instead of 763 (1.20.1) for better compatibility with servers like Hypixel
        packet_id = b'\x00'
        protocol_version = self._write_varint(47)  # Changed from 763 to 47
        host_bytes = host.encode('utf-8')
        host_len = self._write_varint(len(host_bytes))
        port_bytes = struct.pack('>H', port)
        next_state_bytes = self._write_varint(next_state)
        
        data = packet_id + protocol_version + host_len + host_bytes + port_bytes + next_state_bytes
        await self._send_packet(writer, data)

    async def _send_login_start(self, writer, name: str):
        # For Protocol 47 (1.8.9), Login Start only requires the name
        # UUID is NOT required for 1.8.x
        packet_id = b'\x00'
        
        # Player Name (String)
        name_bytes = name.encode('utf-8')
        name_len = self._write_varint(len(name_bytes))
        
        # Protocol 47 (1.8.9) format: Just packet ID + name
        # No UUID needed for 1.8.x compatibility
        data = packet_id + name_len + name_bytes
        
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
