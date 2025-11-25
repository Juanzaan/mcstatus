import sqlite3
import sys

def check_popular_servers():
    conn = sqlite3.connect('data/servers.db')
    c = conn.cursor()
    
    targets = ['hypixel', 'donut', 'minehut', '2b2t', 'universocraft']
    
    print(f"{'SERVER':<30} | {'IP':<25} | {'ONLINE':<8} | {'ALTERNATES'}")
    print("-" * 100)
    
    found_any = False
    for t in targets:
        query = f"%{t}%"
        c.execute('''
            SELECT 
                s.ip, 
                s.alternate_ips,
                (SELECT online FROM server_snapshots WHERE ip=s.ip ORDER BY scan_id DESC LIMIT 1) as online,
                (SELECT MAX(scan_id) FROM server_snapshots WHERE ip=s.ip) as last_scan
            FROM servers s 
            WHERE s.ip LIKE ? OR s.alternate_ips LIKE ?
        ''', (query, query))
        
        rows = c.fetchall()
        for row in rows:
            found_any = True
            ip = row[0]
            alts = row[1][:30] + "..." if row[1] and len(row[1]) > 30 else str(row[1])
            online = str(row[2]) if row[2] is not None else "NONE"
            print(f"{t:<30} | {ip:<25} | {online:<8} | {alts}")

    if not found_any:
        print("❌ NO POPULAR SERVERS FOUND IN DB")
        
    conn.close()

if __name__ == "__main__":
    check_popular_servers()
