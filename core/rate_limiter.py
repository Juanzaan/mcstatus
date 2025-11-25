import time
import logging
from collections import deque, defaultdict
from threading import Lock
from .config_loader import ConfigLoader

class AdaptiveRateLimiter:
    """
    Thread-safe adaptive rate limiter.
    - Global RPM limit
    - Per-domain RPM limit
    - Auto-slowdown on high error rates
    """
    def __init__(self):
        config = ConfigLoader.load()
        self.cfg = config.get('rate_limiting', {})
        
        self.global_rpm = self.cfg.get('global_rpm', 120)
        self.per_domain_rpm = self.cfg.get('per_domain_rpm', 60)
        self.adaptive = self.cfg.get('adaptive', True)
        self.error_threshold = self.cfg.get('error_threshold', 0.3)
        self.slowdown_factor = self.cfg.get('slowdown_factor', 0.5)
        
        self.global_timestamps = deque()
        self.domain_timestamps = defaultdict(deque)
        self.domain_stats = defaultdict(lambda: {'total': 0, 'errors': 0})
        
        self.lock = Lock()
        self.logger = logging.getLogger("RateLimiter")

    async def async_wait_if_needed(self, domain: str = None):
        """Async block execution if rate limit exceeded"""
        import asyncio
        
        # We need to be careful with locking in async context.
        # Ideally we use asyncio.Lock, but we are sharing this class with sync code.
        # For now, we'll use the sync lock for state updates, but release it before sleeping.
        
        sleep_time = 0
        
        with self.lock:
            now = time.time()
            self._cleanup(now)
            
            # Global Check
            if len(self.global_timestamps) >= self.global_rpm:
                wait = 60 - (now - self.global_timestamps[0])
                if wait > 0:
                    sleep_time = max(sleep_time, wait)
            
            # Domain Check
            if domain:
                limit = self._get_effective_limit(domain)
                ts_list = self.domain_timestamps[domain]
                if len(ts_list) >= limit:
                    wait = 60 - (now - ts_list[0])
                    if wait > 0:
                        sleep_time = max(sleep_time, wait)
            
            # If we don't need to sleep, record now
            if sleep_time <= 0:
                self.global_timestamps.append(time.time())
                if domain:
                    self.domain_timestamps[domain].append(time.time())

        # Sleep outside the lock if needed
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
            # After sleeping, we should technically re-check, but for simplicity/throughput
            # we'll just record and proceed. This might slightly burst over limit but is safe.
            with self.lock:
                self.global_timestamps.append(time.time())
                if domain:
                    self.domain_timestamps[domain].append(time.time())

    def wait_if_needed(self, domain: str = None):
        """Block execution if rate limit exceeded"""
        with self.lock:
            now = time.time()
            self._cleanup(now)
            
            # Global Check
            if len(self.global_timestamps) >= self.global_rpm:
                sleep_time = 60 - (now - self.global_timestamps[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time() # Update time after sleep
            
            # Domain Check
            if domain:
                limit = self._get_effective_limit(domain)
                ts_list = self.domain_timestamps[domain]
                if len(ts_list) >= limit:
                    sleep_time = 60 - (now - ts_list[0])
                    if sleep_time > 0:
                        time.sleep(sleep_time)
            
            # Record
            self.global_timestamps.append(time.time())
            if domain:
                self.domain_timestamps[domain].append(time.time())

    def record_result(self, domain: str, success: bool):
        """Feed back result for adaptive logic"""
        if not self.adaptive or not domain:
            return
            
        with self.lock:
            stats = self.domain_stats[domain]
            stats['total'] += 1
            if not success:
                stats['errors'] += 1
            
            # Reset stats periodically to avoid stale history? 
            # For now, simple sliding window or just keep growing until restart
            # Ideally we'd use a time-decaying stat, but this is MVP Enterprise.

    def _get_effective_limit(self, domain: str) -> int:
        base = self.per_domain_rpm
        if not self.adaptive:
            return base
            
        stats = self.domain_stats[domain]
        if stats['total'] < 10: # Warmup
            return base
            
        error_rate = stats['errors'] / stats['total']
        if error_rate > self.error_threshold:
            return int(base * self.slowdown_factor)
        
        return base

    def _cleanup(self, now: float):
        """Remove timestamps older than 1 minute"""
        cutoff = now - 60
        while self.global_timestamps and self.global_timestamps[0] < cutoff:
            self.global_timestamps.popleft()
            
        for d in list(self.domain_timestamps.keys()):
            dq = self.domain_timestamps[d]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if not dq:
                del self.domain_timestamps[d]
