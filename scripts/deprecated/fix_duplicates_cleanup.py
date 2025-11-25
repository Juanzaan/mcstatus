import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def fix_duplicates():
    """
    Fix duplicates by merging servers with same normalized IP.
    Keeps the server with most data/snapshots and merges alternate IPs.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=== DUPLICATE FIX ===")
    
    # Get all servers
    cursor.execute("SELECT ip FROM servers")
    all_ips = [row[0] for row in cursor.fetchall()]
    
    # Group by normalized IP
    from collections import defaultdict
    normalized_groups = defaultdict(list)
    
    for ip in all_ips:
        norm = ip.lower()
        if norm.endswith(':25565'):
            norm = norm[:-6]
        normalized_groups[norm].append(ip)
    
    # Find duplicates
    duplicates = {k: v for k, v in normalized_groups.items() if len(v) > 1}
    
    print(f"Found {len(duplicates)} groups of duplicates")
    
    deleted_count = 0
    for norm, ips in duplicates.items():
        # Sort by number of snapshots (keep the one with most data)
        ip_snapshot_counts = []
        for ip in ips:
            cursor.execute("SELECT COUNT(*) FROM server_snapshots WHERE ip = ?", (ip,))
            count = cursor.fetchone()[0]
            ip_snapshot_counts.append((ip, count))
        
        ip_snapshot_counts.sort(key=lambda x: x[1], reverse=True)
        keeper = ip_snapshot_counts[0][0]
        to_delete = [ip for ip, _ in ip_snapshot_counts[1:]]
        
        # Merge alternate IPs
        cursor.execute("SELECT alternate_ips FROM servers WHERE ip = ?", (keeper,))
        existing_alts = cursor.fetchone()[0]
        if existing_alts:
            alts_list = [a.strip() for a in existing_alts.split(',')]
        else:
            alts_list = []
        
        for ip in to_delete:
            if ip not in alts_list:
                alts_list.append(ip)
        
        # Update keeper with merged alternates
        merged_alts = ','.join(alts_list)
        cursor.execute("UPDATE servers SET alternate_ips = ? WHERE ip = ?", (merged_alts, keeper))
        
        # Delete duplicates (snapshots and server)
        for ip in to_delete:
            cursor.execute("DELETE FROM server_snapshots WHERE ip = ?", (ip,))
            cursor.execute("DELETE FROM servers WHERE ip = ?", (ip,))
            deleted_count += 1
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM servers")
    remaining = cursor.fetchone()[0]
    
    print(f"✅ Duplicate fix complete!")
    print(f"Deleted: {deleted_count} duplicate servers")
    print(f"Remaining: {remaining} servers")
    
    conn.close()

if __name__ == "__main__":
    fix_duplicates()
