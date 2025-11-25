"""
Root vs Subdomain Audit Script
Detects cases where a root domain (ejemplo.com) and its subdomains (play.ejemplo.com)
coexist as separate is_canonical=1 servers.

Uses domain simplicity logic to identify which should be master.
"""
import sqlite3
import sys
from collections import defaultdict
from typing import List, Dict, Tuple

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DB_FILE = 'data/servers.db'


def extract_root_domain(hostname: str) -> str:
    """
    Extract root domain from hostname.
    Examples:
        play.example.com -> example.com
        mc.server.net -> server.net
        example.com -> example.com
    """
    # Remove port if present
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    parts = hostname.split('.')
    
    # If already a root domain (2 parts), return as-is
    if len(parts) <= 2:
        return hostname
    
    # Return last 2 parts (root domain)
    return '.'.join(parts[-2:])


def calculate_domain_score(hostname: str) -> int:
    """
    Calculate domain simplicity score.
    Higher score = simpler = better canonical candidate
    """
    # Remove port
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    dot_count = hostname.count('.')
    length = len(hostname)
    
    # Same scoring as DeduplicationEngine
    score = -(dot_count * 10000) - (length * 100)
    return score


def audit_root_duplicates() -> Dict:
    """
    Audit database for root vs subdomain conflicts.
    Returns report dict with findings.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("🔎 Root vs Subdomain Audit")
    print("=" * 80)
    
    # Get all canonical servers
    cursor.execute("""
        SELECT ip FROM servers WHERE is_canonical = 1 ORDER BY ip
    """)
    canonical_servers = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📊 Total canonical servers: {len(canonical_servers)}")
    
    # Group by root domain
    root_groups = defaultdict(list)
    for server in canonical_servers:
        root = extract_root_domain(server)
        root_groups[root].append(server)
    
    # Find conflicts (multiple canonical servers with same root)
    conflicts = []
    
    for root, servers in root_groups.items():
        if len(servers) > 1:
            # Calculate scores for each server
            scored_servers = []
            for server in servers:
                score = calculate_domain_score(server)
                scored_servers.append((server, score))
            
            # Sort by score (highest = simplest)
            scored_servers.sort(key=lambda x: x[1], reverse=True)
            
            # Best candidate is highest score
            master_candidate = scored_servers[0]
            aliases_candidates = scored_servers[1:]
            
            conflicts.append({
                'root_domain': root,
                'master': master_candidate[0],
                'master_score': master_candidate[1],
                'aliases': [(ip, score) for ip, score in aliases_candidates],
                'score_differences': [master_candidate[1] - score for _, score in aliases_candidates]
            })
    
    conn.close()
    
    # Print report
    print(f"\n📋 AUDIT RESULTS:")
    print(f"  Root domains with conflicts: {len(conflicts)}")
    
    if conflicts:
        print(f"\n⚠️  CONFLICTS DETECTED:")
        print("=" * 80)
        
        for i, conflict in enumerate(conflicts, 1):
            print(f"\n{i}. Root Domain: {conflict['root_domain']}")
            print(f"   Master Candidate: {conflict['master']} (score: {conflict['master_score']})")
            print(f"   Aliases to consolidate:")
            for j, ((alias_ip, alias_score), score_diff) in enumerate(zip(conflict['aliases'], conflict['score_differences']), 1):
                print(f"      {j}) {alias_ip:40} (score: {alias_score:6}, diff: +{score_diff})")
        
        print("\n" + "=" * 80)
        print(f"📊 SUMMARY:")
        total_aliases = sum(len(c['aliases']) for c in conflicts)
        print(f"  Total conflicts: {len(conflicts)}")
        print(f"  Servers to consolidate: {total_aliases}")
        print(f"  Canonical count after fix: {len(canonical_servers) - total_aliases}")
        
    else:
        print(f"\n✅ NO CONFLICTS DETECTED!")
        print(f"   All root domains have only one canonical server.")
        print(f"   Database is clean.")
    
    return {
        'total_canonical': len(canonical_servers),
        'conflicts': conflicts,
        'clean': len(conflicts) == 0
    }


if __name__ == '__main__':
    try:
        report = audit_root_duplicates()
        
        if not report['clean']:
            print(f"\n💡 RECOMMENDATION:")
            print(f"   Run a mass consolidation script to merge these conflicts.")
            print(f"   Expected result: {report['total_canonical'] - sum(len(c['aliases']) for c in report['conflicts'])} canonical servers")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
