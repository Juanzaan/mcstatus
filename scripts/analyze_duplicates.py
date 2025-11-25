import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def analyze():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("--- Analysis Report ---")
    
    # 1. Check for Case Duplicates
    cursor.execute("""
        SELECT LOWER(ip), COUNT(*), GROUP_CONCAT(ip)
        FROM servers 
        GROUP BY LOWER(ip) 
        HAVING COUNT(*) > 1
    """)
    case_dupes = cursor.fetchall()
    print(f"\n1. Case-insensitive duplicates found: {len(case_dupes)}")
    for row in case_dupes[:10]:
        print(f"   - {row[0]}: {row[2]}")
        
    # 2. Check for Port 25565 Redundancy
    # Find pairs where one has :25565 and the other doesn't
    cursor.execute("SELECT ip FROM servers")
    all_ips = {row[0] for row in cursor.fetchall()}
    
    port_dupes = []
    for ip in all_ips:
        if ip.endswith(":25565"):
            clean_ip = ip[:-6]
            if clean_ip in all_ips:
                port_dupes.append((clean_ip, ip))
                
    print(f"\n2. Port 25565 redundancy found: {len(port_dupes)}")
    for pair in port_dupes[:10]:
        print(f"   - {pair[0]} vs {pair[1]}")

    conn.close()

if __name__ == "__main__":
    analyze()
