import sqlite3
import os

DB_FILE = os.path.join("data", "servers.db")

def fix_duplicates():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    print("--- Starting Cleanup ---")
    
    # 1. Fix Case Duplicates
    print("\n1. Fixing Case Duplicates...")
    cursor.execute("""
        SELECT ip FROM servers 
        WHERE ip != LOWER(ip)
    """)
    mixed_case_ips = [row[0] for row in cursor.fetchall()]
    
    for bad_ip in mixed_case_ips:
        good_ip = bad_ip.lower()
        print(f"Processing: {bad_ip} -> {good_ip}")
        
        # Check if good_ip already exists
        cursor.execute("SELECT 1 FROM servers WHERE ip = ?", (good_ip,))
        exists = cursor.fetchone()
        
        if exists:
            print(f"  Merging {bad_ip} into existing {good_ip}")
            try:
                # Reassign snapshots
                cursor.execute("""
                    UPDATE server_snapshots SET ip = ? WHERE ip = ?
                """, (good_ip, bad_ip))
                
                # Delete bad server entry
                cursor.execute("DELETE FROM servers WHERE ip = ?", (bad_ip,))
                conn.commit()
            except sqlite3.IntegrityError as e:
                print(f"  Error merging: {e}")
                conn.rollback()
        else:
            print(f"  Renaming {bad_ip} to {good_ip}")
            try:
                # Update server entry (cascade should handle snapshots if configured, but let's be safe)
                # Actually, we can't update PK if target exists (handled above)
                # Here target doesn't exist, so we can just update
                cursor.execute("UPDATE servers SET ip = ? WHERE ip = ?", (good_ip, bad_ip))
                # Update snapshots manually if cascade isn't on
                cursor.execute("UPDATE server_snapshots SET ip = ? WHERE ip = ?", (good_ip, bad_ip))
                conn.commit()
            except Exception as e:
                print(f"  Error renaming: {e}")
                conn.rollback()

    # 2. Fix Port 25565 Redundancy
    print("\n2. Fixing Port 25565 Redundancy...")
    cursor.execute("""
        SELECT ip FROM servers 
        WHERE ip LIKE '%:25565'
    """)
    port_ips = [row[0] for row in cursor.fetchall()]
    
    for bad_ip in port_ips:
        good_ip = bad_ip[:-6] # Remove :25565
        print(f"Processing: {bad_ip} -> {good_ip}")
        
        cursor.execute("SELECT 1 FROM servers WHERE ip = ?", (good_ip,))
        exists = cursor.fetchone()
        
        if exists:
            print(f"  Merging {bad_ip} into existing {good_ip}")
            try:
                cursor.execute("""
                    UPDATE server_snapshots SET ip = ? WHERE ip = ?
                """, (good_ip, bad_ip))
                cursor.execute("DELETE FROM servers WHERE ip = ?", (bad_ip,))
                conn.commit()
            except Exception as e:
                print(f"  Error merging: {e}")
                conn.rollback()
        else:
            print(f"  Renaming {bad_ip} to {good_ip}")
            try:
                cursor.execute("UPDATE servers SET ip = ? WHERE ip = ?", (good_ip, bad_ip))
                cursor.execute("UPDATE server_snapshots SET ip = ? WHERE ip = ?", (good_ip, bad_ip))
                conn.commit()
            except Exception as e:
                print(f"  Error renaming: {e}")
                conn.rollback()

    conn.close()
    print("\n--- Cleanup Complete ---")

if __name__ == "__main__":
    fix_duplicates()
