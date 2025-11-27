"""
Enterprise MongoDB Persistence Layer
------------------------------------
Async MongoDB operations for server data persistence.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger("EnterprisePersistence")

class MongoDBPersistence:
    """
    Handles all MongoDB operations for server data.
    Uses motor for async operations.
    """
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", database: str = "mcstatus"):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection URI
            database: Database name
        """
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(connection_string)
        self.db: AsyncIOMotorDatabase = self.client[database]
        self.servers_collection = self.db.servers
        self.events_collection = self.db.verification_events
        
    async def initialize(self):
        """
        Create indexes and setup database.
        Should be called once during application startup.
        """
        logger.info("Initializing MongoDB indexes...")
        
        # Create indexes for servers collection
        await self.servers_collection.create_index([("ip", 1), ("port", 1)], unique=True)
        await self.servers_collection.create_index([("type", 1), ("status", 1)])
        await self.servers_collection.create_index([("last_verified", -1)])
        await self.servers_collection.create_index([("players.online", -1)])
        
        # Create index for events collection (optional)
        await self.events_collection.create_index([("server_ip", 1), ("timestamp", -1)])
        
        logger.info("MongoDB initialized successfully")
    
    async def upsert_server(self, result: Dict[str, Any]) -> bool:
        """
        Insert or update a server record.
        
        Args:
            result: Server result from Enterprise Verifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            meta = result['metadata']
            
            # Parse IP and port
            target = result['target']
            if ":" in target:
                ip, port_str = target.split(":")
                port = int(port_str)
            else:
                ip = target
                port = 25565
            
            # Determine status
            status = "offline" if result['type'] in ['OFFLINE', 'UNKNOWN'] else "online"
            
            # Prepare document
            now = datetime.utcnow()
            
            update_doc = {
                "$set": {
                    "ip": ip,
                    "port": port,
                    "type": result['type'],
                    "status": status,
                    "version": meta.get('version', 'Unknown'),
                    "motd": str(meta.get('motd', '')),
                    "players": {
                        "online": meta.get('players_online', 0),
                        "max": meta.get('players_max', 0)
                    },
                    "latency": meta.get('latency', 0),
                    "last_verified": now,
                },
                "$setOnInsert": {
                    "first_seen": now,
                    "source": "enterprise_pipeline"
                },
                "$inc": {
                    "verification_count": 1
                }
            }
            
            # Also update last_seen if server is online
            if status == "online":
                update_doc["$set"]["last_seen"] = now
            
            # Upsert operation
            await self.servers_collection.update_one(
                {"ip": ip, "port": port},
                update_doc,
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting server {result.get('target')}: {e}")
            return False
    
    async def upsert_batch(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Upsert multiple servers in batch.
        
        Args:
            results: List of server results
            
        Returns:
            Statistics dict with success/fail counts
        """
        stats = {"success": 0, "failed": 0}
        
        tasks = [self.upsert_server(result) for result in results]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                stats["failed"] += 1
            elif result:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Batch upsert complete: {stats['success']} success, {stats['failed']} failed")
        return stats
    
    async def get_server(self, ip: str, port: int = 25565) -> Optional[Dict[str, Any]]:
        """
        Retrieve a server by IP and port.
        """
        return await self.servers_collection.find_one({"ip": ip, "port": port})
    
    async def get_servers_by_type(self, server_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get servers of a specific type.
        
        Args:
            server_type: PREMIUM, SEMI_PREMIUM, NON_PREMIUM
            limit: Max results
        """
        cursor = self.servers_collection.find(
            {"type": server_type, "status": "online"}
        ).sort("players.online", -1).limit(limit)
        
        return await cursor.to_list(length=limit)
    
    async def get_stats(self) -> Dict[str, int]:
        """
        Get overall statistics.
        """
        stats = {
            "total": await self.servers_collection.count_documents({}),
            "online": await self.servers_collection.count_documents({"status": "online"}),
            "premium": await self.servers_collection.count_documents({"type": "PREMIUM", "status": "online"}),
            "semi_premium": await self.servers_collection.count_documents({"type": "SEMI_PREMIUM", "status": "online"}),
            "non_premium": await self.servers_collection.count_documents({"type": "NON_PREMIUM", "status": "online"}),
        }
        return stats
    
    async def close(self):
        """Close MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")


# Example usage
async def test_persistence():
    """Test MongoDB persistence."""
    db = MongoDBPersistence()
    
    try:
        await db.initialize()
        
        # Test data
        test_result = {
            "target": "mc.hypixel.net",
            "type": "PREMIUM",
            "metadata": {
                "ip": "mc.hypixel.net",
                "port": 25565,
                "latency": 45.2,
                "version": "1.8-1.21",
                "motd": "Hypixel Network",
                "players_online": 40000,
                "players_max": 200000
            },
            "timestamp": 1700000000
        }
        
        # Upsert
        success = await db.upsert_server(test_result)
        print(f"Upsert: {'✅' if success else '❌'}")
        
        # Retrieve
        server = await db.get_server("mc.hypixel.net")
        print(f"Retrieved: {server['ip'] if server else 'Not found'}")
        
        # Stats
        stats = await db.get_stats()
        print(f"Stats: {stats}")
        
    finally:
        await db.close()


if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_persistence())
