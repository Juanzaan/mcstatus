import time
import random
import logging
import threading
import os
from typing import Optional, Dict, List
from .config_loader import ConfigLoader

class ProxyManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProxyManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        config = ConfigLoader.load()
        self.cfg = config.get('proxies', {})
        self.enabled = self.cfg.get('enabled', False)
        self.mode = self.cfg.get('mode', 'round_robin')
        self.cooldown = self.cfg.get('cooldown_seconds', 300)
        self.max_failures = self.cfg.get('max_failures', 3)
        
        self.proxies = []
        self.proxy_stats = {} # {proxy: {'failures': 0, 'last_used': 0, 'cooldown_until': 0, 'weight': 100}}
        self.lock = threading.Lock()
        self.logger = logging.getLogger("ProxyManager")
        
        self._load_proxies()
        self._initialized = True

    def _load_proxies(self):
        # Load from config list
        sources = self.cfg.get('sources', [])
        self.proxies.extend(sources)
        
        # Load from file
        file_path = self.cfg.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    lines = [l.strip() for l in f if l.strip()]
                    self.proxies.extend(lines)
            except Exception as e:
                self.logger.error(f"Failed to load proxies from {file_path}: {e}")
        
        # Deduplicate
        self.proxies = list(set(self.proxies))
        
        # Initialize stats
        for p in self.proxies:
            self.proxy_stats[p] = {
                'failures': 0, 
                'last_used': 0, 
                'cooldown_until': 0, 
                'weight': 100
            }
            
        self.logger.info(f"Loaded {len(self.proxies)} proxies. Enabled: {self.enabled}")

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Returns a proxy dict for requests/selenium or None if disabled/exhausted"""
        if not self.enabled or not self.proxies:
            return None
            
        with self.lock:
            now = time.time()
            available = [
                p for p in self.proxies 
                if self.proxy_stats[p]['cooldown_until'] <= now
            ]
            
            if not available:
                self.logger.warning("All proxies are on cooldown!")
                return None
            
            selected = None
            if self.mode == 'weighted':
                weights = [self.proxy_stats[p]['weight'] for p in available]
                selected = random.choices(available, weights=weights, k=1)[0]
            else:
                # Round robin (random for now for simplicity in stateless)
                selected = random.choice(available)
                
            self.proxy_stats[selected]['last_used'] = now
            
            return {
                "http": selected,
                "https": selected
            }

    def report_success(self, proxy_url: str):
        if not proxy_url or not self.enabled:
            return
            
        # Extract url if passed as dict
        if isinstance(proxy_url, dict):
            proxy_url = proxy_url.get('http')
            
        with self.lock:
            if proxy_url in self.proxy_stats:
                stats = self.proxy_stats[proxy_url]
                stats['failures'] = 0
                stats['weight'] = min(stats['weight'] + 1, 200) # Cap weight

    def report_failure(self, proxy_url: str):
        if not proxy_url or not self.enabled:
            return

        if isinstance(proxy_url, dict):
            proxy_url = proxy_url.get('http')

        with self.lock:
            if proxy_url in self.proxy_stats:
                stats = self.proxy_stats[proxy_url]
                stats['failures'] += 1
                stats['weight'] = max(stats['weight'] - 10, 1)
                
                if stats['failures'] >= self.max_failures:
                    stats['cooldown_until'] = time.time() + self.cooldown
                    stats['failures'] = 0 # Reset count after triggering cooldown
                    self.logger.warning(f"Proxy {proxy_url} placed on cooldown for {self.cooldown}s")
