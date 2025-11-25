"""
Enrichment Scanner
Populates favicon_hash and resolved_ip fields for existing servers.

This must be run BEFORE deduplication to ensure fingerprints are available.
"""

import sqlite3
import hashlib
import dns.resolver
from datetime import datetime
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.deduplication_engine import DeduplicationService

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "servers.db")

class EnrichmentScanner:
    """
    Scans existing servers and populates:
    - favicon_hash (from icon field)
    - resolved_ip (DNS lookup)
    """
    
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.dedup_service = DeduplicationService(db_path)
    
    def enrich_favicons(self):
        """Generate and store favicon hashes for all servers with icons"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("🔍 Enriching favicon hashes...")
        
        cursor.execute("""
            SELECT ip, icon
            FROM servers
            WHERE icon IS NOT NULL AND favicon_hash IS NULL
        """)
        
        servers = cursor.fetchall()
        total = len(servers)
        
        print(f"Found {total} servers with icons to hash")
        
        updated = 0
        for i, server in enumerate(servers, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{total}")
            
            favicon_hash = self.dedup_service.hash_favicon(server['icon'])
            
            cursor.execute("""
                UPDATE servers
                SET favicon_hash = ?
                WHERE ip = ?
            """, (favicon_hash, server['ip']))
            
            updated += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated {updated} favicon hashes")
    
    def enrich_dns(self, rate_limit: float = 0.1):
        """
        Resolve DNS for all servers.
        
        Args:
            rate_limit: Seconds to wait between requests (default 0.1s = 10/sec)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print("🔍 Enriching DNS resolutions...")
        print(f"  Rate limit: {1/rate_limit:.0f} requests/second")
        
        cursor.execute("""
            SELECT ip
            FROM servers
            WHERE resolved_ip IS NULL
        """)
        
        servers = cursor.fetchall()
        total = len(servers)
        
        print(f"Found {total} servers without DNS resolution")
        
        updated = 0
        failed = 0
        
        for i, server in enumerate(servers, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{total} (Updated: {updated}, Failed: {failed})")
            
            resolved_ip = self.dedup_service.resolve_dns(server['ip'])
            
            if resolved_ip:
                updated += 1
            else:
                failed += 1
            
            # Rate limiting
            time.sleep(rate_limit)
        
        print(f"✅ Resolved {updated} DNS records ({failed} failed)")
    
    def run_full_enrichment(self):
        """Run complete enrichment scan"""
        print("=" * 60)
        print("ENRICHMENT SCANNER - Phase 10")
        print("=" * 60)
        print()
        
        self.enrich_favicons()
        print()
        self.enrich_dns()
        
        print()
        print("=" * 60)
        print("✅ Enrichment Complete")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Run: python scripts/master_dedup.py --mode dry-run")
        print("2. Review the deduplication report")
        print("3. Run: python scripts/master_dedup.py --mode auto --threshold 0.9")

if __name__ == "__main__":
    scanner = EnrichmentScanner()
    scanner.run_full_enrichment()
