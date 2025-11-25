"""
Mass consolidation script for root vs subdomain conflicts.
Automatically merges all detected conflicts from audit.
"""
import sqlite3
from collections import defaultdict

DB_FILE = 'data/servers.db'

def extract_root_domain(hostname):
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    parts = hostname.split('.')
    if len(parts) <= 2:
        return hostname
    return '.'.join(parts[-2:])

def calculate_domain_score(hostname):
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    dot_count = hostname.count('.')
    length = len(hostname)
    return -(dot_count * 10000) - (length * 100)

print("Mass Root vs Subdomain Consolidation")
print("=" * 80)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Get all canonical servers
cursor.execute("SELECT ip FROM servers WHERE is_canonical = 1 ORDER BY ip")
canonical_servers = [row[0] for row in cursor.fetchall()]

print(f"\nBefore: {len(canonical_servers)} canonical servers")

# Group by root domain
root_groups = defaultdict(list)
for server in canonical_servers:
    root = extract_root_domain(server)
    root_groups[root].append(server)

# Process conflicts
total_updated = 0
total_added_to_aliases = 0
conflicts_fixed = 0

for root, servers in root_groups.items():
    if len(servers) > 1:
        # Calculate scores
        scored_servers = [(s, calculate_domain_score(s)) for s in servers]
        scored_servers.sort(key=lambda x: x[1], reverse=True)
        
        master = scored_servers[0][0]
        aliases = [ip for ip, _ in scored_servers[1:]]
        
        conflicts_fixed += 1
        print(f"\n{conflicts_fixed}. Consolidating {root}:")
        print(f"   Master: {master}")
        
        for alias in aliases:
            # Mark as alias
            cursor.execute("""
                UPDATE servers
                SET is_canonical = 0, canonical_id = ?
                WHERE ip = ?
            """, (master, alias))
            total_updated += 1
            
            # Add to server_aliases
            cursor.execute("""
                INSERT OR IGNORE INTO server_aliases 
                (alias_ip, canonical_ip, detection_method, confidence_score)
                VALUES (?, ?, 'mass_root_consolidation', 1.0)
            """, (alias, master))
            if cursor.rowcount > 0:
                total_added_to_aliases += 1
            
            print(f"   -> {alias}")
        
        # Ensure master is canonical
        cursor.execute("""
            UPDATE servers
            SET is_canonical = 1, canonical_id = NULL
            WHERE ip = ?
        """, (master,))

conn.commit()

# Verify results
cursor.execute("SELECT COUNT(*) FROM servers WHERE is_canonical = 1")
final_canonical = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM servers WHERE is_canonical = 0")
final_aliases = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM server_aliases")
alias_entries = cursor.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print("CONSOLIDATION COMPLETE!")
print(f"  Conflicts fixed: {conflicts_fixed}")
print(f"  Servers updated: {total_updated}")
print(f"  Aliases added: {total_added_to_aliases}")
print(f"\nFINAL STATE:")
print(f"  Canonical servers: {final_canonical}")
print(f"  Alias servers: {final_aliases}")
print(f"  server_aliases entries: {alias_entries}")
print(f"  Total: {final_canonical + final_aliases}")
print("=" * 80)
