"""
Add alternate_ips field to database and track duplicate variants.

This script creates a mapping of normalized IPs to their variant forms,
storing them in the database for frontend display.
"""

import sqlite3
import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import normalize_server_address, DB_FILE


def add_alternate_ips_column():
    """Add alternate_ips column to servers table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            ALTER TABLE servers ADD COLUMN alternate_ips TEXT DEFAULT NULL
        """)
        conn.commit()
        print("✅ Added alternate_ips column")
    except sqlite3.OperationalError as e:
        if "duplicate" in str(e).lower():
            print("ℹ️  Column already exists")
        else:
            raise
    finally:
        conn.close()


def populate_alternate_ips():
    """
    Find all variant IPs that normalize to the same value and store them.
    
    Before deduplication, we had variants like:
    - play.hypixel.net, Play.Hypixel.NET, play.hypixel.net:25565
    
    After deduplication, we only have play.hypixel.net.
    This function would track what WOULD have been duplicates for historical data.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # For existing data, we don't have pre-dedup records
    # But we can note if normalization changed the IP
    cursor.execute("SELECT ip FROM servers")
    all_ips = [row[0] for row in cursor.fetchall()]
    
    updates = []
    for ip in all_ips:
        normalized = normalize_server_address(ip)
        if normalized != ip:
            # This IP was normalized (shouldn't happen after our fixes, but check)
            updates.append((f"[Original: {ip}]", normalized))
    
    if updates:
        print(f"Found {len(updates)} IPs that differ from normalized form")
        for alt_text, ip in updates:
            cursor.execute("""
                UPDATE servers 
                SET alternate_ips = ?
                WHERE ip = ?
            """, (alt_text, ip))
    
    conn.commit()
    conn.close()
    print(f"✅ Updated {len(updates)} servers with alternate IP info")


if __name__ == "__main__":
    print("=== Adding Alternate IPs Support ===\n")
    add_alternate_ips_column()
    populate_alternate_ips()
    print("\n✅ Complete")
