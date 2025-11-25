import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def deep_analysis():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=== DEEP ANALYSIS ===\n")
    
    # 1. Check total servers
    cursor.execute("SELECT COUNT(*) FROM servers")
    total = cursor.fetchone()[0]
    print(f"Total servers in DB: {total}")
    
    # 2. Check auth_mode distribution
    print("\n--- Auth Mode Distribution ---")
    cursor.execute("""
        SELECT auth_mode, COUNT(*) as count
        FROM servers
        GROUP BY auth_mode
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0] or 'NULL'}: {row[1]}")
    
    # 3. Check premium/cracked count from latest snapshots
    print("\n--- Premium/Cracked from Latest Snapshots ---")
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN s.auth_mode = 'PREMIUM' THEN 1 ELSE 0 END) as premium,
            SUM(CASE WHEN s.auth_mode = 'NO-PREMIUM' THEN 1 ELSE 0 END) as cracked,
            SUM(CASE WHEN s.auth_mode IS NULL OR (s.auth_mode != 'PREMIUM' AND s.auth_mode != 'NO-PREMIUM') THEN 1 ELSE 0 END) as other
        FROM servers s
        JOIN server_snapshots ss ON s.ip = ss.ip
        WHERE ss.id = (SELECT MAX(id) FROM server_snapshots WHERE ip = s.ip)
    """)
    row = cursor.fetchone()
    print(f"  Total: {row[0]}")
    print(f"  Premium: {row[1]}")
    print(f"  Non-Premium: {row[2]}")
    print(f"  Other/NULL: {row[3]}")
    print(f"  Sum check: {row[1] + row[2] + row[3]} (should equal {row[0]})")
    
    # 4. Advanced duplicate detection
    print("\n--- Advanced Duplicate Detection ---")
    cursor.execute("SELECT ip FROM servers")
    all_ips = [row[0] for row in cursor.fetchall()]
    
    # Normalize and group
    from collections import defaultdict
    groups = defaultdict(list)
    
    for ip in all_ips:
        # Multiple normalization strategies
        norm = ip.lower()
        
        # Remove port if default
        if norm.endswith(':25565'):
            norm = norm[:-6]
        
        # Remove www
        if norm.startswith('www.'):
            norm = norm[4:]
        
        # Group by base domain (for subdomains)
        parts = norm.split('.')
        if len(parts) > 2:
            # Could be subdomain, check if it's a common pattern
            # e.g., server.example.com vs example.com
            base = '.'.join(parts[-2:])  # Get last two parts
            groups[base].append(ip)
        else:
            groups[norm].append(ip)
    
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Potential duplicate groups: {len(duplicates)}")
    
    if len(duplicates) > 0:
        print("\nFirst 10 duplicate groups:")
        for i, (norm, ips) in enumerate(list(duplicates.items())[:10]):
            print(f"  {norm}: {ips}")
    
    # 5. Exact duplicates (should be 0)
    cursor.execute("""
        SELECT ip, COUNT(*) as count
        FROM servers
        GROUP BY ip
        HAVING count > 1
    """)
    exact_dups = cursor.fetchall()
    if exact_dups:
        print(f"\n⚠️ EXACT DUPLICATES FOUND: {len(exact_dups)}")
        for ip, count in exact_dups[:5]:
            print(f"  {ip}: {count} entries")
    else:
        print("\n✅ No exact IP duplicates found")
    
    conn.close()

if __name__ == "__main__":
    deep_analysis()
