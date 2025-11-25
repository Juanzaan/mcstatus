import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def find_and_fix_invalid_auth_modes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=== FINDING INVALID AUTH_MODE VALUES ===\n")
    
    # Find servers with invalid auth_mode
    cursor.execute("""
        SELECT ip, auth_mode
        FROM servers
        WHERE auth_mode IS NULL 
           OR (auth_mode NOT IN ('PREMIUM', 'CRACKED', 'NO-PREMIUM'))
    """)
    
    invalid_servers = cursor.fetchall()
    
    if len(invalid_servers) == 0:
        print("✅ No invalid auth_mode values found")
        conn.close()
        return
    
    print(f"Found {len(invalid_servers)} servers with invalid auth_mode:")
    for ip, auth_mode in invalid_servers:
        print(f"  {ip}: '{auth_mode}'")
    
    # Normalize them to 'CRACKED'
    print("\nNormalizing to 'CRACKED'...")
    for ip, _ in invalid_servers:
        cursor.execute("UPDATE servers SET auth_mode = 'CRACKED' WHERE ip = ?", (ip,))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Fixed {len(invalid_servers)} servers")

if __name__ == "__main__":
    find_and_fix_invalid_auth_modes()
