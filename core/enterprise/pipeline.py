"""
Enterprise Pipeline Orchestrator
--------------------------------
Orchestrates the full data processing workflow:
1. Scrape IPs from multiple sources
2. Verify and Classify using Enterprise Engine
3. Save results (JSON/DB)
"""

import asyncio
import logging
import json
import os
import sys
from typing import List, Set
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.enterprise.verifier import EnterpriseVerifier
# Import scrapers (assuming they can be imported or we run them as subprocesses)
# For now, we'll simulate scraper execution or read their output files
# Real integration would involve importing scraper functions directly

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnterprisePipeline")

class EnterprisePipeline:
    def __init__(self, data_dir: str = "data", use_mongodb: bool = False, mongo_uri: str = "mongodb://localhost:27017/"):
        self.data_dir = Path(data_dir)
        self.verifier = EnterpriseVerifier(concurrency=200, timeout=5.0)
        self.use_mongodb = use_mongodb
        self.mongo_uri = mongo_uri
        self.db = None
        
    async def run_pipeline(self):
        logger.info("🚀 Starting Enterprise Pipeline...")
        
        # Initialize MongoDB if enabled
        if self.use_mongodb:
            try:
                from .persistence import MongoDBPersistence
                self.db = MongoDBPersistence(self.mongo_uri)
                await self.db.initialize()
                logger.info("✅ MongoDB initialized")
            except Exception as e:
                logger.error(f"Failed to initialize MongoDB: {e}")
                logger.info("Falling back to JSON output")
                self.use_mongodb = False
        
        # Phase 1: Collection (Scraping)
        # In a real scenario, we would trigger scrapers here.
        # For this integration, we will read existing scraped files or run scrapers.
        # Let's assume we want to process all IPs found in data/*.json files
        raw_ips = self._collect_ips()
        logger.info(f"Phase 1 Complete. Collected {len(raw_ips)} unique IPs.")
        
        if not raw_ips:
            logger.warning("No IPs found to process. Exiting.")
            return

        # Phase 2: Verification & Classification (The Enterprise Engine)
        logger.info("Phase 2: Starting Mass Verification...")
        results = await self.verifier.verify_batch(list(raw_ips))
        
        # Phase 3: Processing & Saving
        logger.info("Phase 3: Processing Results...")
        
        if self.use_mongodb and self.db:
            # Save to MongoDB
            await self._save_to_mongodb(results)
        else:
            # Save to JSON (legacy)
            processed_data = self._process_results(results)
            self._save_results(processed_data)
        
        logger.info("✅ Pipeline Complete!")
        
        # Cleanup
        if self.db:
            await self.db.close()

    def _collect_ips(self) -> Set[str]:
        """
        Collects IPs from various sources (scraped files, raw text lists, etc.)
        """
        ips = set()
        
        # 1. Load from existing scraped JSONs
        scraper_files = [
            "minecraft_server_list_300pages_*.json",
            "namemc_servers_*.json",
            "scraped_servers.json"
        ]
        
        for pattern in scraper_files:
            for file_path in self.data_dir.glob(pattern):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Handle different formats (list of dicts, dict with 'servers' key)
                        server_list = data if isinstance(data, list) else data.get('servers', [])
                        
                        for s in server_list:
                            if isinstance(s, dict):
                                ip = s.get('ip') or s.get('address')
                            else:
                                ip = str(s)
                                
                            if ip:
                                ips.add(ip)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    
        # 2. Load from raw text files if any
        txt_files = self.data_dir.glob("*.txt")
        for file_path in txt_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        ip = line.strip()
                        if ip and not ip.startswith('#'):
                            ips.add(ip)
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")

        return ips

    def _process_results(self, results: List[dict]) -> dict:
        """
        Organize results by category
        """
        output = {
            "premium": [],
            "semi_premium": [],
            "non_premium": [],
            "offline": [],
            "stats": {
                "total_scanned": len(results),
                "premium": 0,
                "semi_premium": 0,
                "non_premium": 0,
                "offline": 0
            }
        }
        
        for res in results:
            category = res['type'].lower()
            metadata = res['metadata']
            
            # Normalize structure for saving
            server_entry = {
                "ip": res['target'],
                "type": res['type'],
                "online": metadata['players_online'],
                "max_players": metadata['players_max'],
                "version": metadata['version'],
                "motd": metadata['motd'],
                "latency": metadata['latency'],
                "last_seen": res['timestamp']
            }
            
            if category == "premium":
                output["premium"].append(server_entry)
                output["stats"]["premium"] += 1
            elif category == "semi_premium":
                output["semi_premium"].append(server_entry)
                output["stats"]["semi_premium"] += 1
            elif category == "non_premium":
                output["non_premium"].append(server_entry)
                output["stats"]["non_premium"] += 1
            else: # offline or unknown
                output["offline"].append(server_entry)
                output["stats"]["offline"] += 1
                
        return output

    def _save_results(self, data: dict):
        """
        Save processed results to disk
        """
        output_file = self.data_dir / "enterprise_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Results saved to {output_file}")
        
        # Also print summary
        stats = data['stats']
        print("\n📊 Pipeline Summary:")
        print(f"  Total Scanned: {stats['total_scanned']}")
        print(f"  Premium:       {stats['premium']}")
        print(f"  Semi-Premium:  {stats['semi_premium']}")
        print(f"  Non-Premium:   {stats['non_premium']}")
        print(f"  Offline:       {stats['offline']}")
    
    async def _save_to_mongodb(self, results: List[dict]):
        """
        Save results to MongoDB
        """
        logger.info(f"Saving {len(results)} servers to MongoDB...")
        stats = await self.db.upsert_batch(results)
        
        # Get final stats from DB
        db_stats = await self.db.get_stats()
        
        print("\n📊 MongoDB Summary:")
        print(f"  Upserted: {stats['success']} success, {stats['failed']} failed")
        print(f"\n  Database Totals:")
        print(f"  • Total Servers: {db_stats['total']}")
        print(f"  • Online: {db_stats['online']}")
        print(f"  • Premium: {db_stats['premium']}")
        print(f"  • Semi-Premium: {db_stats['semi_premium']}")
        print(f"  • Non-Premium: {db_stats['non_premium']}")

if __name__ == "__main__":
    # Fix for Windows asyncio loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    pipeline = EnterprisePipeline()
    asyncio.run(pipeline.run_pipeline())
