"""
Enterprise API - FastAPI REST API for Minecraft Server Data
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from datetime import datetime
from typing import Optional, Literal
import math

from .models import ServerResponse, ServerListResponse, StatsResponse
from core.enterprise.persistence import MongoDBPersistence

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnterpriseAPI")

# Initialize FastAPI
app = FastAPI(
    title="Minecraft Server API",
    description="Enterprise API for Minecraft server data classification and statistics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
db: Optional[MongoDBPersistence] = None

async def get_db():
    """Dependency to get database connection"""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    global db
    try:
        db = MongoDBPersistence()
        await db.initialize()
        logger.info("API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    if db:
        await db.close()
        logger.info("API shutdown complete")

# Endpoints

@app.get("/", tags=["Root"])
@limiter.limit("60/minute")
async def root(request):
    """API root endpoint"""
    return {
        "name": "Minecraft Server API",
        "version": "1.0.0",
        "endpoints": {
            "servers": "/servers",
            "server_detail": "/servers/{ip}",
            "stats": "/stats/summary"
        }
    }

@app.get("/servers", response_model=ServerListResponse, tags=["Servers"])
@limiter.limit("30/minute")
async def list_servers(
    request,
    type: Optional[Literal["PREMIUM", "SEMI_PREMIUM", "NON_PREMIUM"]] = None,
    status: Literal["online", "offline"] = "online",
    page: int = Query(1, ge=1, le=1000),
    page_size: int = Query(50, ge=1, le=1000),
    sort_by: Literal["players", "name", "last_verified"] = "players",
    sort_order: Literal["asc", "desc"] = "desc",
    database: MongoDBPersistence = Depends(get_db)
):
    """
    List servers with filters and pagination.
    
    **Filters:**
    - type: Server type (PREMIUM, SEMI_PREMIUM, NON_PREMIUM)
    - status: online or offline
    
    **Pagination:**
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 1000)
    
    **Sorting:**
    - sort_by: players, name, or last_verified
    - sort_order: asc or desc
    """
    try:
        # Build query
        query = {"status": status}
        if type:
            query["type"] = type
        
        # Map sort_by to MongoDB field
        sort_field_map = {
            "players": "players.online",
            "name": "ip",
            "last_verified": "last_verified"
        }
        sort_field = sort_field_map.get(sort_by, "players.online")
        sort_direction = -1 if sort_order == "desc" else 1
        
        # Get total count
        total = await database.servers_collection.count_documents(query)
        
        # Calculate pagination
        skip = (page - 1) * page_size
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        # Query servers
        cursor = database.servers_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(page_size)
        servers_raw = await cursor.to_list(length=page_size)
        
        # Convert to response model
        servers = []
        for s in servers_raw:
            servers.append(ServerResponse(
                ip=s["ip"],
                port=s.get("port", 25565),
                type=s["type"],
                status=s["status"],
                version=s.get("version", "Unknown"),
                motd=s.get("motd", ""),
                players={"online": s["players"]["online"], "max": s["players"]["max"]},
                latency=s.get("latency", 0),
                first_seen=s.get("first_seen", datetime.utcnow()),
                last_seen=s.get("last_seen", datetime.utcnow()),
                last_verified=s.get("last_verified", datetime.utcnow()),
                verification_count=s.get("verification_count", 0)
            ))
        
        return ServerListResponse(
            servers=servers,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/servers/{ip}", response_model=ServerResponse, tags=["Servers"])
@limiter.limit("60/minute")
async def get_server(
    request,
    ip: str,
    port: int = Query(25565, ge=1, le=65535),
    database: MongoDBPersistence = Depends(get_db)
):
    """
    Get server details by IP and port.
    
    **Parameters:**
    - ip: Server IP address or hostname
    - port: Server port (default: 25565)
    """
    try:
        server = await database.get_server(ip, port)
        
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        return ServerResponse(
            ip=server["ip"],
            port=server.get("port", 25565),
            type=server["type"],
            status=server["status"],
            version=server.get("version", "Unknown"),
            motd=server.get("motd", ""),
            players={"online": server["players"]["online"], "max": server["players"]["max"]},
            latency=server.get("latency", 0),
            first_seen=server.get("first_seen", datetime.utcnow()),
            last_seen=server.get("last_seen", datetime.utcnow()),
            last_verified=server.get("last_verified", datetime.utcnow()),
            verification_count=server.get("verification_count", 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching server {ip}:{port}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats/summary", response_model=StatsResponse, tags=["Statistics"])
@limiter.limit("60/minute")
async def get_stats(
    request,
    database: MongoDBPersistence = Depends(get_db)
):
    """
    Get aggregate statistics for all servers.
    
    **Returns:**
    - Total servers count
    - Online servers count
    - Breakdown by type (Premium, Semi-Premium, Non-Premium)
    - Total player count across all online servers
    """
    try:
        stats = await database.get_stats()
        
        # Calculate total players
        pipeline = [
            {"$match": {"status": "online"}},
            {"$group": {"_id": None, "total_players": {"$sum": "$players.online"}}}
        ]
        result = await database.servers_collection.aggregate(pipeline).to_list(1)
        total_players = result[0]["total_players"] if result else 0
        
        return StatsResponse(
            total=stats["total"],
            online=stats["online"],
            premium=stats["premium"],
            semi_premium=stats["semi_premium"],
            non_premium=stats["non_premium"],
            total_players=total_players,
            last_updated=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}
