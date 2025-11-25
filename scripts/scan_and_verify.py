"""
AsyncIO Enterprise Minecraft Server Scanner
-------------------------------------------
High-performance, asynchronous scanner using SQLite for persistence.

Features:
- AsyncIO for high concurrency (thousands of servers/sec)
- Direct SQLite integration (no more JSON files)
- Batch processing for efficient DB writes
- Adaptive rate limiting
- Auto-tuning resources

Usage:
    python scan_and_verify.py [--workers 500] [--batch-size 50]
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Set, Any
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config_loader import ConfigLoader
from core.logger import setup_logger
from core.rate_limiter import AdaptiveRateLimiter
from core import database as db

# Auto-install dependencies
try:
    from mcstatus import JavaServer
    import psutil
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcstatus", "psutil", "aiofiles"])
    from mcstatus import JavaServer
    import psutil

class AsyncScanner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config = ConfigLoader.load()
        
        # Setup Logger
        log_file = os.path.join(self.config['paths']['logs_dir'], "async_scanner.log")
        self.logger = setup_logger("AsyncScanner", log_file)
        
        self.rate_limiter = AdaptiveRateLimiter()
        self.scan_id = None
        self.results_buffer = []
        self.buffer_lock = asyncio.Lock()
        
    async def scan_server(self, server_data: Dict, semaphore: asyncio.Semaphore) -> Dict:
        """Scan a single server asynchronously."""
        ip = server_data['ip']
        result = server_data.copy()
        result['checked_at'] = datetime.now().isoformat()
        
        async with semaphore:
            # Rate Limit Check
            await self.rate_limiter.async_wait_if_needed()
            
            if self.args.dry_run:
                await asyncio.sleep(0.01)
                result.update({
                    'online': True,
                    'auth_mode': 'CRACKED',
                    'players_actual': 0,
                    'players_max': 100,
                    'version': '1.20.4',
                    'latency': 10.0,
                    'description': 'Dry Run Server',
                    'sample_size': 0,
                    'premium': 0,
                    'cracked': 0,
                    'new_players': 0
                })
                return result

            try:
                timeout = self.config['resources'].get('timeout_default', 5)
                
                # Async lookup
                server = await JavaServer.async_lookup(ip, timeout=timeout)
                
                # Async status
                status = await server.async_status()
                
                result.update({
                    'online': True,
                    'players_actual': status.players.online,
                    'players_max': status.players.max,
                    'version': status.version.name,
                    'latency': status.latency,
                    'description': str(status.description)
                })

                # Auth Mode Detection
                auth_mode = "UNKNOWN"
                desc = str(status.description).lower()
                if any(x in desc for x in ['cracked', 'no premium', 'offline', 'tlauncher']):
                    auth_mode = "CRACKED"
                elif any(x in desc for x in ['premium only', 'hypixel']):
                    auth_mode = "PREMIUM"
                
                # Heuristic fallback
                if auth_mode == "UNKNOWN":
                    if status.players.online > 100:
                        auth_mode = "PREMIUM"
                    else:
                        auth_mode = "CRACKED"
                
                result['auth_mode'] = auth_mode
                
                extra = {'context': {'ip': ip, 'players': result['players_actual'], 'auth': auth_mode}}
                self.logger.info(f"✅ {ip:30} | {result['players_actual']:4}p | {auth_mode}", extra=extra)
                
                self.rate_limiter.record_result(domain=None, success=True)

            except Exception as e:
                result['online'] = False
                result['error'] = str(e)
                if result.get('auth_mode') == 'UNKNOWN':
                    result['auth_mode'] = 'UNKNOWN'
                
                # self.logger.debug(f"❌ {ip}: {e}") # Too noisy
                self.rate_limiter.record_result(domain=None, success=False)
            
            return result

    async def save_buffer(self):
        """Flush results buffer to database."""
        async with self.buffer_lock:
            if not self.results_buffer:
                return
            
            batch = self.results_buffer[:]
            self.results_buffer.clear()
            
        if batch:
            self.logger.info(f"💾 Saving batch of {len(batch)} results...")
            # Run blocking DB call in executor
            try:
                await asyncio.to_thread(db.save_batch_results, self.scan_id, batch)
            except Exception as e:
                self.logger.error(f"Error saving batch: {e}")

    async def run(self):
        # Initialize DB
        db.init_db()
        self.scan_id = db.create_scan()
        self.logger.info(f"🚀 Starting Scan ID: {self.scan_id}")
        
        # Load targets from DB
        targets = db.get_servers_to_scan(limit=self.args.limit, order_by=self.args.order)
        self.logger.info(f"🎯 Loaded {len(targets)} targets from database")
        
        if not targets:
            self.logger.warning("⚠️ No targets found in database.")
            return

        # Configure concurrency
        max_workers = self.args.workers
        semaphore = asyncio.Semaphore(max_workers)
        
        tasks = []
        for target in targets:
            task = asyncio.create_task(self.scan_server(target, semaphore))
            tasks.append(task)
            
        # Process results as they complete
        completed = 0
        total = len(tasks)
        
        for future in asyncio.as_completed(tasks):
            result = await future
            
            should_save = False
            async with self.buffer_lock:
                self.results_buffer.append(result)
                
                if len(self.results_buffer) >= self.args.batch_size:
                    should_save = True
            
            if should_save:
                await self.save_buffer()
            
            completed += 1
            if completed % 100 == 0:
                print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%)")

        # Final flush
        await self.save_buffer()
        self.logger.info("✅ Scan complete!")

def main():
    parser = argparse.ArgumentParser(description="AsyncIO Minecraft Server Scanner")
    parser.add_argument("--workers", type=int, default=500, help="Max concurrent tasks")
    parser.add_argument("--batch-size", type=int, default=50, help="DB write batch size")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of servers to scan")
    parser.add_argument("--order", choices=['last_seen', 'random'], default='last_seen', help="Scan order")
    parser.add_argument("--dry-run", action="store_true", help="Simulate scan")
    
    args = parser.parse_args()
    
    scanner = AsyncScanner(args)
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(scanner.run())

if __name__ == "__main__":
    main()
