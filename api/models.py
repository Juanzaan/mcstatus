"""
API Models - Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Response Models

class PlayerStats(BaseModel):
    """Player statistics"""
    online: int = Field(ge=0, description="Current online players")
    max: int = Field(ge=0, description="Maximum player capacity")

class ServerResponse(BaseModel):
    """Server detail response"""
    ip: str = Field(..., description="Server IP address")
    port: int = Field(default=25565, ge=1, le=65535)
    type: Literal["PREMIUM", "SEMI_PREMIUM", "NON_PREMIUM", "OFFLINE", "UNKNOWN"]
    status: Literal["online", "offline"]
    version: str
    motd: str = Field(default="")
    players: PlayerStats
    latency: float = Field(ge=0, description="Latency in milliseconds")
    first_seen: datetime
    last_seen: datetime
    last_verified: datetime
    verification_count: int = Field(ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ip": "mc.hypixel.net",
                "port": 25565,
                "type": "PREMIUM",
                "status": "online",
                "version": "1.8-1.21",
                "motd": "Hypixel Network",
                "players": {"online": 42000, "max": 200000},
                "latency": 45.2,
                "first_seen": "2025-11-26T00:00:00Z",
                "last_seen": "2025-11-26T22:00:00Z",
                "last_verified": "2025-11-26T22:00:00Z",
                "verification_count": 142
            }
        }

class ServerListResponse(BaseModel):
    """Paginated server list response"""
    servers: list[ServerResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=1000)
    total_pages: int = Field(ge=0)

class StatsResponse(BaseModel):
    """Aggregate statistics"""
    total: int = Field(ge=0)
    online: int = Field(ge=0)
    premium: int = Field(ge=0)
    semi_premium: int = Field(ge=0)
    non_premium: int = Field(ge=0)
    total_players: Optional[int] = Field(default=0, ge=0)
    last_updated: datetime

# Query Parameters

class ServerFilters(BaseModel):
    """Query parameters for server list endpoint"""
    type: Optional[Literal["PREMIUM", "SEMI_PREMIUM", "NON_PREMIUM"]] = None
    status: Optional[Literal["online", "offline"]] = "online"
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=50, ge=1, le=1000)
    sort_by: Literal["players", "name", "last_verified"] = "players"
    sort_order: Literal["asc", "desc"] = "desc"
