"""
Enterprise Verifier Engine
--------------------------
High-performance async engine for mass server verification.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Callable, Awaitable
from .detector import IntelligentDetector, ServerType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnterpriseVerifier")

class EnterpriseVerifier:
    def __init__(self, concurrency: int = 500, timeout: float = 5.0):
        self.concurrency = concurrency
        self.timeout = timeout
        self.detector = IntelligentDetector()
        self.queue = asyncio.Queue()
        self.results = []
        self.active_workers = 0
        self.start_time = 0
        self.processed_count = 0

    async def verify_batch(self, targets: List[str]) -> List[Dict[str, Any]]:
        """
        Verify a batch of servers (IP:Port strings).
        """
        self.start_time = time.time()
        self.results = []
        self.processed_count = 0
        
        # Populate queue
        for target in targets:
            await self.queue.put(target)
            
        logger.info(f"Starting verification of {len(targets)} servers with {self.concurrency} workers...")
        
        # Start workers
        workers = []
        for i in range(min(self.concurrency, len(targets))):
            worker = asyncio.create_task(self._worker(f"Worker-{i}"))
            workers.append(worker)
            
        # Wait for queue to be empty
        await self.queue.join()
        
        # Cancel workers
        for worker in workers:
            worker.cancel()
            
        await asyncio.gather(*workers, return_exceptions=True)
        
        duration = time.time() - self.start_time
        rate = self.processed_count / duration if duration > 0 else 0
        logger.info(f"Verification complete. Processed {self.processed_count} servers in {duration:.2f}s ({rate:.2f} servers/sec)")
        
        return self.results

    async def _worker(self, name: str):
        self.active_workers += 1
        try:
            while True:
                try:
                    target = await self.queue.get()
                    
                    # Parse IP:Port
                    if ":" in target:
                        ip, port_str = target.split(":")
                        port = int(port_str)
                    else:
                        ip = target
                        port = 25565
                        
                    # Detect
                    server_type, metadata = await self.detector.detect(ip, port, self.timeout)
                    
                    result = {
                        "target": target,
                        "type": server_type.value,
                        "metadata": metadata,
                        "timestamp": time.time()
                    }
                    
                    self.results.append(result)
                    self.processed_count += 1
                    
                    if self.processed_count % 100 == 0:
                        logger.info(f"Progress: {self.processed_count} verified...")
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker error processing {target}: {e}")
                finally:
                    self.queue.task_done()
        finally:
            self.active_workers -= 1
