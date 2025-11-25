import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join("data", "servers.db")

def delete_offline_servers():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print(f"=== OFFLINE SERVER DELETION ===")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Backup: data/servers_backup.db")
    
    # Get list of offline server IPs (based on latest snapshot)
    cursor.execute("""
        SELECT s.ip
        FROM servers s
        JOIN server_snapshots ss ON s.ip = ss.ip
        WHERE ss.id = (SELECT MAX(id) FROM server_snapshots WHERE ip = s.ip)
        AND ss.online = 0
    """)
    offline_ips = [row[0] for row in cursor.fetchall()]
    
    print(f"\nServers to delete: {len(offline_ips)}")
    
    if len(offline_ips) == 0:
        print("No offline servers to delete.")
        conn.close()
        return
    
    # Delete snapshots first (to avoid foreign key issues)
    for ip in offline_ips:
        cursor.execute("DELETE FROM server_snapshots WHERE ip = ?", (ip,))
    
    # Delete from servers table
    for ip in offline_ips:
        cursor.execute("DELETE FROM servers WHERE ip = ?", (ip,))
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM servers")
    remaining = cursor.fetchone()[0]
    
    print(f"\n✅ Deletion complete!")
    print(f"Deleted: {len(offline_ips)} servers")
    print(f"Remaining: {remaining} servers")
    
    conn.close()

if __name__ == "__main__":
    delete_offline_servers()
