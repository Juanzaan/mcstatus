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
    
    # Known Semi-Premium Networks (Large established hybrid servers)
    KNOWN_SEMI_PREMIUM_NETWORKS = [
        "universocraft",
        "librecraft",
        "survivaldub",
        "nostalgia",
        "arkania",
        "starmade",
        "earthmc"
    ]
    
    # Authentication Plugin Signatures
    # These plugins enable hybrid auth on cracked servers
    AUTH_PLUGIN_SIGNATURES = [
        "authme",
        "librelogin",
        "jpremium",
        "premiumconnector",
        "fastlogin",
        "nlogin",
        "ultimatelogin",
        "hybrid",
        "semi-premium",
        "premium & cracked",
        "premium y pirata",
        "premium and cracked",
        "modo híbrido",
        "modo hibrido"
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
                # For NON_PREMIUM protocol servers, check if they're semi-premium
                # by analyzing additional factors
                if self._is_likely_semi_premium(metadata):
                    return ServerType.SEMI_PREMIUM, metadata
                return ServerType.NON_PREMIUM, metadata
            else:
                # If protocol check is inconclusive, default to UNKNOWN
                return ServerType.UNKNOWN, metadata

        except asyncio.TimeoutError:
            return ServerType.OFFLINE, metadata
        except Exception as e:
            logger.debug(f"Detection error for {ip}: {e}")
            return ServerType.OFFLINE, metadata

    def _check_heuristics(self, metadata: Dict[str, Any]) -> Optional[ServerType]:
        """Check for known signatures in MOTD or Hostname"""
        motd = str(metadata.get("motd", "")).lower()
        ip = metadata.get("ip", "").lower()
        
        # Check for known semi-premium networks by domain/IP
        for network in self.KNOWN_SEMI_PREMIUM_NETWORKS:
            if network in ip or network in motd:
                return ServerType.SEMI_PREMIUM
        
        # Check for auth plugin signatures in MOTD
        for plugin_sig in self.AUTH_PLUGIN_SIGNATURES:
            if plugin_sig in motd:
                return ServerType.SEMI_PREMIUM
        
        # Common Cracked Signatures (definitive non-premium)
        if "cracked" in motd or "no premium" in motd or "offline" in motd or "pirata" in motd:
            # But check if they also mention hybrid/semi-premium
            if any(sig in motd for sig in self.AUTH_PLUGIN_SIGNATURES):
                return ServerType.SEMI_PREMIUM
            return ServerType.NON_PREMIUM
            
        return None
    
    def _is_likely_semi_premium(self, metadata: Dict[str, Any]) -> bool:
        """
        Secondary check for semi-premium servers that passed protocol as NON_PREMIUM.
        Uses heuristics to identify established hybrid networks.
        """
        motd = str(metadata.get("motd", "")).lower()
        players_online = metadata.get("players_online", 0)
        
        # Large player count (>100) + NON_PREMIUM protocol could indicate
        # a popular hybrid network
        if players_online > 100:
            # Check if MOTD hints at hybrid support
            hybrid_keywords = [
                "premium", "original", "oficial", "pirata",
                "java", "bedrock", "cracked", "login"
            ]
            keyword_count = sum(1 for kw in hybrid_keywords if kw in motd)
            
            # If multiple keywords present, likely advertising hybrid support
            if keyword_count >= 2:
                return True
        
        return False

