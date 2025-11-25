import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def aggressive_dedup():
    """
    Aggressively deduplicate by:
    1. Removing port variations (server.com:25565 vs server.com)
    2. Removing www prefix variations
    3. Merging subdomain variations (for certain patterns)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=== AGGRESSIVE DEDUPLICATION ===\n")
    
    cursor.execute("SELECT ip, COUNT(*) FROM servers GROUP BY ip")
    original_count = len(cursor.fetchall())
    print(f"Starting servers: {original_count}")
    
    # Get all servers
    cursor.execute("SELECT ip FROM servers")
    all_ips = [row[0] for row in cursor.fetchall()]
    
    # Group by aggressive normalization
    from collections import defaultdict
    groups = defaultdict(list)
    
    for ip in all_ips:
        norm = ip.lower()
        
        # Remove port
        if ':' in norm:
            norm = norm.split(':')[0]
        
        # Remove www
        if norm.startswith('www.'):
            norm = norm[4:]
        
        groups[norm].append(ip)
    
    # Find and merge duplicates
    deleted = 0
    for norm, ips in groups.items():
        if len(ips) > 1:
            # Keep the shortest one (most canonical)
            ips.sort(key=lambda x: (len(x), x))
            keeper = ips[0]
            to_delete = ips[1:]
            
            print(f"Merging {norm}: keeping '{keeper}', deleting {to_delete}")
            
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
            
            merged_alts = ','.join(alts_list)
            cursor.execute("UPDATE servers SET alternate_ips = ? WHERE ip = ?", (merged_alts, keeper))
            
            # Delete duplicates
            for ip in to_delete:
                cursor.execute("DELETE FROM server_snapshots WHERE ip = ?", (ip,))
                cursor.execute("DELETE FROM servers WHERE ip = ?", (ip,))
                deleted += 1
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM servers")
    final_count = cursor.fetchone()[0]
    
    print(f"\n✅ Aggressive deduplication complete!")
    print(f"Deleted: {deleted} duplicates")
    print(f"Final count: {final_count} servers")
    
    conn.close()

if __name__ == "__main__":
    aggressive_dedup()
