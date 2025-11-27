"""
Enterprise Intelligent Server Detector
--------------------------------------
Advanced logic to classify Minecraft servers by analyzing their protocol behavior.
"""

import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from mcstatus import JavaServer

# Configure logging
logger = logging.getLogger("EnterpriseDetector")

class ServerType(Enum):
    PREMIUM = "PREMIUM"
    SEMI_PREMIUM = "SEMI_PREMIUM"
    NON_PREMIUM = "NON_PREMIUM"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"

from .protocol import DeepProtocolAnalyzer, AuthMode

class IntelligentDetector:
    """
    Analyzes server behavior to determine its authentication mode.
    """
    
    KNOWN_SEMI_PREMIUM_SIGNATURES = [
        "universocraft",
        "librecraft",
        "survivaldub",
        "nostalgia"
    ]

    def __init__(self):
        self.protocol_analyzer = DeepProtocolAnalyzer()

    async def detect(self, ip: str, port: int = 25565, timeout: float = 5.0) -> Tuple[ServerType, Dict[str, Any]]:
        """
        Main entry point for detection.
        Returns (ServerType, Metadata)
        """
        metadata = {
            "ip": ip,
            "port": port,
            "latency": 0,
            "version": "Unknown",
            "motd": "",
            "players_online": 0,
            "players_max": 0
        }

        try:
            # 1. Basic Status Ping (Fast check)
            server = await JavaServer.async_lookup(f"{ip}:{port}", timeout=timeout)
            status = await server.async_status()
            
            metadata["latency"] = status.latency
            metadata["version"] = status.version.name
            metadata["motd"] = status.description
            metadata["players_online"] = status.players.online
            metadata["players_max"] = status.players.max
            
            # 2. Heuristic Analysis (Name/MOTD signatures)
            heuristic_type = self._check_heuristics(metadata)
            if heuristic_type:
                return heuristic_type, metadata

            # 3. Protocol Analysis (Deep check)
            # Perform deep handshake to check for EncryptionRequest
            auth_mode = await self.protocol_analyzer.analyze_auth_mode(ip, port)
            
            if auth_mode == AuthMode.PREMIUM:
                return ServerType.PREMIUM, metadata
            elif auth_mode == AuthMode.NON_PREMIUM:
                return ServerType.NON_PREMIUM, metadata
            else:
                # If protocol check is inconclusive, default to UNKNOWN or NON_PREMIUM based on context
                # For safety, UNKNOWN is better than False Positive Premium
                return ServerType.UNKNOWN, metadata

        except asyncio.TimeoutError:
            return ServerType.OFFLINE, metadata
        except Exception as e:
            logger.debug(f"Detection error for {ip}: {e}")
            return ServerType.OFFLINE, metadata

    def _check_heuristics(self, metadata: Dict[str, Any]) -> Optional[ServerType]:
        """Check for known signatures in MOTD or Hostname"""
        motd = str(metadata.get("motd", "")).lower()
        
        # Semi-Premium Signatures
        for sig in self.KNOWN_SEMI_PREMIUM_SIGNATURES:
            if sig in motd:
                return ServerType.SEMI_PREMIUM
        
        # Common Cracked Signatures
        if "cracked" in motd or "no premium" in motd or "offline" in motd:
            return ServerType.NON_PREMIUM
            
        return None
