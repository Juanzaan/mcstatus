"""
Unified Deduplication Engine
Detects duplicates through multiple strategies:
- String normalization (legacy)
- Favicon fingerprinting
- DNS resolution
- Player sample matching
"""

import sqlite3
import hashlib
import socket
import dns.resolver
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import difflib
import os

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "servers.db")
DNS_CACHE_TTL = timedelta(hours=48)  # User decision: 48 hours


@dataclass
class ServerFingerprint:
    """Fingerprint of a server for duplicate detection"""
    ip: str
    favicon_hash: Optional[str]
    resolved_ip: Optional[str]
    player_sample: List[str]  # UUIDs or names
    player_count: int
    motd: str
    
    def __hash__(self):
        return hash(self.ip)


@dataclass
class DuplicateMatch:
    """A detected duplicate pair with confidence score"""
    master_ip: str
    alias_ip: str
    confidence: float
    detection_method: str
    reason: str


class DeduplicationService:
    """
    Unified deduplication service with multi-strategy detection.
    
    User Decisions Implemented:
    - Favicon: Hash in aliases, full base64 only in canonical
    - DNS Cache: 48 hours TTL
    - Aliases: Hidden in public frontend, searchable, admin view available
    - Migration: Schema first, then enrichment scan, then merge
    """
    
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = 2
        self.dns_resolver.lifetime = 2
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========== FINGERPRINTING ==========
    
    def hash_favicon(self, favicon_base64: str) -> str:
        """Generate SHA256 hash of favicon"""
        if not favicon_base64:
            return None
        return hashlib.sha256(favicon_base64.encode()).hexdigest()
    
    def resolve_dns(self, hostname: str) -> Optional[str]:
        """
        Resolve hostname to IP address.
        Checks cache first (48h TTL).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check cache
        cursor.execute("""
            SELECT resolved_ip, last_dns_check
            FROM servers
            WHERE ip = ?
        """, (hostname,))
        row = cursor.fetchone()
        
        if row and row['resolved_ip'] and row['last_dns_check']:
            last_check = datetime.fromisoformat(row['last_dns_check'])
            if datetime.now() - last_check < DNS_CACHE_TTL:
                conn.close()
                return row['resolved_ip']
        
        # Resolve fresh
        try:
            # Extract hostname from IP:PORT format
            if ':' in hostname:
                hostname = hostname.split(':')[0]
            
            answers = self.dns_resolver.resolve(hostname, 'A')
            resolved_ip = str(answers[0])
            
            # Update cache
            cursor.execute("""
                UPDATE servers
                SET resolved_ip = ?, last_dns_check = ?
                WHERE ip = ?
            """, (resolved_ip, datetime.now().isoformat(), hostname))
            conn.commit()
            conn.close()
            
            return resolved_ip
        except Exception as e:
            print(f"DNS resolution failed for {hostname}: {e}")
            conn.close()
            return None
    
    def get_fingerprint(self, server_ip: str) -> ServerFingerprint:
        """Generate fingerprint for a server"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.ip, s.favicon_hash, s.resolved_ip, ss.online, ss.version
            FROM servers s
            JOIN server_snapshots ss ON s.ip = ss.ip
            WHERE s.ip = ? AND ss.id = (
                SELECT MAX(id) FROM server_snapshots WHERE ip = s.ip
            )
        """, (server_ip,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # TODO: Fetch player sample from snapshots (needs schema extension)
        player_sample = []
        
        return ServerFingerprint(
            ip=row['ip'],
            favicon_hash=row['favicon_hash'],
            resolved_ip=row['resolved_ip'],
            player_sample=player_sample,
            player_count=row['online'] or 0,
            motd=row['version'] or ''  # Using version as MOTD placeholder
        )
    
    # ========== DETECTION STRATEGIES ==========
    
    def detect_by_dns(self) -> List[DuplicateMatch]:
        """Strategy 1: Same resolved IP (100% confidence)"""
        matches = []
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT resolved_ip, GROUP_CONCAT(ip) as ips
            FROM servers
            WHERE resolved_ip IS NOT NULL
            GROUP BY resolved_ip
            HAVING COUNT(*) > 1
        """)
        
        for row in cursor.fetchall():
            ips = row['ips'].split(',')
            master = self._select_canonical(ips)
            for alias in ips:
                if alias != master:
                    matches.append(DuplicateMatch(
                        master_ip=master,
                        alias_ip=alias,
                        confidence=1.0,
                        detection_method='dns_resolution',
                        reason=f'Both resolve to {row["resolved_ip"]}'
                    ))
        
        conn.close()
        return matches
    
    def detect_by_favicon_and_players(self) -> List[DuplicateMatch]:
        """Strategy 2: Same favicon hash + similar player count (85% confidence)"""
        matches = []
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                s.favicon_hash,
                s.ip,
                ss.online
            FROM servers s
            JOIN server_snapshots ss ON s.ip = ss.ip
            WHERE s.favicon_hash IS NOT NULL
              AND ss.id = (SELECT MAX(id) FROM server_snapshots WHERE ip = s.ip)
        """)
        
        # Group by favicon hash
        groups = defaultdict(list)
        for row in cursor.fetchall():
            groups[row['favicon_hash']].append((row['ip'], row['online'] or 0))
        
        # Find matches within each group
        for favicon_hash, servers in groups.items():
            if len(servers) < 2:
                continue
            
            master = self._select_canonical([ip for ip, _ in servers])
            master_count = next(count for ip, count in servers if ip == master)
            
            for alias_ip, alias_count in servers:
                if alias_ip == master:
                    continue
                
                # Check if player counts are within 5%
                if master_count > 0:
                    diff_pct = abs(alias_count - master_count) / master_count
                    if diff_pct <= 0.05:
                        matches.append(DuplicateMatch(
                            master_ip=master,
                            alias_ip=alias_ip,
                            confidence=0.85,
                            detection_method='favicon_and_players',
                            reason=f'Same favicon, player count diff: {diff_pct:.1%}'
                        ))
        
        conn.close()
        return matches
    
    def detect_by_normalization(self) -> List[DuplicateMatch]:
        """Strategy 3: Aggressive string normalization (70% confidence)"""
        matches = []
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT ip FROM servers")
        all_ips = [row['ip'] for row in cursor.fetchall()]
        
        # Group by normalized form
        groups = defaultdict(list)
        for ip in all_ips:
            norm = self._aggressive_normalize(ip)
            groups[norm].append(ip)
        
        # Find duplicates
        for norm, ips in groups.items():
            if len(ips) > 1:
                master = self._select_canonical(ips)
                for alias in ips:
                    if alias != master:
                        matches.append(DuplicateMatch(
                            master_ip=master,
                            alias_ip=alias,
                            confidence=0.70,
                            detection_method='string_normalization',
                            reason=f'Normalized to: {norm}'
                        ))
        
        conn.close()
        return matches
    
    # ========== CANONICAL SELECTION ==========
    
    def _select_canonical(self, ips: List[str]) -> str:
        """
        UPGRADED: Select canonical with domain simplicity priority.
        
        Priority (highest to lowest):
        1. Domain depth (fewer dots = simpler = MUCH better)
        2. Domain length (shorter name = better)
        3. Age (older first_seen)
        4. Uptime (more snapshots)
        
        Example: minehut.gg (1 dot) beats cookiescafe.minehut.gg (2 dots)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        scores = []
        for ip in ips:
            # Extract hostname (remove port if present)
            hostname = ip.split(':')[0]
            
            # Calculate domain metrics
            dot_count = hostname.count('.')
            hostname_length = len(hostname)
            
            # Fetch server metadata
            cursor.execute("""
                SELECT first_seen,
                       (SELECT COUNT(*) FROM server_snapshots 
                        WHERE server_snapshots.ip = servers.ip) as snapshot_count
                FROM servers
                WHERE ip = ?
            """, (ip,))
            row = cursor.fetchone()
            
            # Calculate age and uptime
            if row and row['first_seen']:
                try:
                    age_days = (datetime.now() - datetime.fromisoformat(row['first_seen'])).days
                except:
                    age_days = 0
            else:
                age_days = 0
            
            snapshot_count = row['snapshot_count'] if row else 0
            
            # Weighted scoring (CRITICAL: Domain simplicity heavily prioritized)
            # - Domain depth: -10,000 points PER DOT (heavily penalize complexity)
            # - Length: -100 points PER CHARACTER (penalize long names)
            # - Age: +1 point per day (reward older servers)
            # - Snapshots: +10 points each (reward uptime)
            total_score = (
                -(dot_count * 10000) +      # minehut.gg (1 dot) gets 10k more than cookiescafe.minehut.gg (2 dots)
                -(hostname_length * 100) +  # Shorter names preferred
                (age_days * 1) +             # Older servers slightly preferred
                (snapshot_count * 10)        # Higher uptime slightly preferred
            )
            
            scores.append((ip, total_score, dot_count, hostname_length))
        
        conn.close()
        
        # Return IP with highest score
        best = max(scores, key=lambda x: x[1])
        print(f"  📌 Selected canonical: {best[0]} (dots: {best[2]}, len: {best[3]}, score: {best[1]})")
        return best[0]
    
    def _aggressive_normalize(self, ip: str) -> str:
        """Aggressive normalization for comparison"""
        norm = ip.lower()
        if ':' in norm:
            norm = norm.split(':')[0]
        if norm.startswith('www.'):
            norm = norm[4:]
        return norm
    
    # ========== ANALYSIS & REPORTING ==========
    
    def analyze(self, strategies: List[str] = None) -> Dict:
        """
        Run duplicate detection with all strategies.
        Returns a report without modifying the database.
        
        Args:
            strategies: List of strategy names to run. If None, runs all.
        """
        if strategies is None:
            strategies = ['dns', 'favicon_and_players', 'normalization']
        
        all_matches = []
        
        print("🔍 Running Deduplication Analysis...")
        
        if 'dns' in strategies:
            print("  ➤ DNS Resolution strategy...")
            all_matches.extend(self.detect_by_dns())
        
        if 'favicon_and_players' in strategies:
            print("  ➤ Favicon + Player Count strategy...")
            all_matches.extend(self.detect_by_favicon_and_players())
        
        if 'normalization' in strategies:
            print("  ➤ String Normalization strategy...")
            all_matches.extend(self.detect_by_normalization())
        
        # Deduplicate matches (same pair detected by multiple strategies)
        unique_matches = {}
        for match in all_matches:
            key = (match.master_ip, match.alias_ip)
            if key not in unique_matches or match.confidence > unique_matches[key].confidence:
                unique_matches[key] = match
        
        matches = list(unique_matches.values())
        
        # Group by confidence
        high_conf = [m for m in matches if m.confidence >= 0.9]
        medium_conf = [m for m in matches if 0.5 <= m.confidence < 0.9]
        low_conf = [m for m in matches if m.confidence < 0.5]
        
        report = {
            'total_matches': len(matches),
            'high_confidence': len(high_conf),
            'medium_confidence': len(medium_conf),
            'low_confidence': len(low_conf),
            'matches': [
                {
                    'master': m.master_ip,
                    'alias': m.alias_ip,
                    'confidence': m.confidence,
                    'method': m.detection_method,
                    'reason': m.reason
                } for m in matches
            ]
        }
        
        print(f"\n✅ Analysis Complete:")
        print(f"  Total Matches: {len(matches)}")
        print(f"  High Confidence (≥90%): {len(high_conf)}")
        print(f"  Medium Confidence (50-90%): {len(medium_conf)}")
        print(f"  Low Confidence (<50%): {len(low_conf)}")
        
        return report
    
    # ========== MERGING ==========
    
    def merge(self, matches: List[DuplicateMatch], dry_run: bool = True):
        """
        Execute merge of duplicates into canonical/alias system.
        
        User Decision: Favicon base64 only stored in canonical, aliases get hash only.
        """
        if dry_run:
            print("🧪 DRY RUN MODE - No changes will be made")
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        merged_count = 0
        
        for match in matches:
            try:
                # Insert into aliases table
                cursor.execute("""
                    INSERT INTO server_aliases (alias_ip, canonical_ip, detection_method, confidence_score)
                    VALUES (?, ?, ?, ?)
                """, (match.alias_ip, match.master_ip, match.detection_method, match.confidence))
                
                # Update alias server record
                cursor.execute("""
                    UPDATE servers
                    SET canonical_id = ?, is_canonical = 0
                    WHERE ip = ?
                """, (match.master_ip, match.alias_ip))
                
                # Update master server record
                cursor.execute("""
                    UPDATE servers
                    SET is_canonical = 1
                    WHERE ip = ?
                """, (match.master_ip,))
                
                merged_count += 1
                
            except sqlite3.IntegrityError as e:
                print(f"⚠️  Skipping {match.alias_ip} → {match.master_ip}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Merged {merged_count} aliases")
