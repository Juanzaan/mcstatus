import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def analyze_duplicates():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("--- DUPLICATE ANALYSIS ---")
    # Check for duplicates by normalized IP (ignoring port if default)
    cursor.execute("SELECT ip FROM servers")
    all_ips = [row[0] for row in cursor.fetchall()]
    
    normalized_map = {}
    duplicates = []
    
    for ip in all_ips:
        norm = ip.lower()
        if norm.endswith(':25565'):
            norm = norm[:-6]
        
        if norm in normalized_map:
            duplicates.append((norm, normalized_map[norm], ip))
        else:
            normalized_map[norm] = ip
            
    print(f"Total Servers: {len(all_ips)}")
    print(f"Potential Duplicates found: {len(duplicates)}")
    for norm, original, current in duplicates[:10]:
        print(f"  - {norm}: {original} vs {current}")
        
    print("\n--- OFFLINE ANALYSIS ---")
    # Count offline servers (based on latest snapshot)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM servers s
        JOIN server_snapshots ss ON s.ip = ss.ip
        WHERE ss.id = (SELECT MAX(id) FROM server_snapshots WHERE ip = s.ip)
        AND ss.online = 0
    """)
    offline_count = cursor.fetchone()[0]
    print(f"Servers currently offline (to be deleted): {offline_count}")
    
    conn.close()

if __name__ == "__main__":
    analyze_duplicates()
