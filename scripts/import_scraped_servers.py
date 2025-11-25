"""
Import scraped servers into SQLite database with normalization.
Handles deduplication and proper schema mapping.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import database as db
from datetime import datetime
import sqlite3

def import_scraped_servers(filepath):
    """
    Import servers from text file into database.
    Each line should contain one server IP/hostname.
    """
    print(f"\n{'='*70}")
    print(" IMPORTING SCRAPED SERVERS TO DATABASE")
    print(f"{'='*70}\n")
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return
    
    # Read IPs
    with open(filepath, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]
    
    print(f"📄 Loaded {len(ips):,} IPs from file")
    
    # Normalize and deduplicate before inserting
    normalized_ips = {}
    for ip in ips:
        normalized = db.normalize_server_address(ip)
        if normalized not in normalized_ips:
            normalized_ips[normalized] = []
        if ip != normalized:
            normalized_ips[normalized].append(ip)
    
    print(f"🔄 Normalized to {len(normalized_ips):,} unique servers")
    variants_found = sum(1 for alts in normalized_ips.values() if alts)
    print(f"🔀 Found {variants_found:,} servers with alternate IPs")
    
    # Insert into database
    conn = sqlite3.connect(db.DB_FILE)
    cursor = conn.cursor()
    
    added = 0
    updated = 0
    
    for normalized_ip, alternates in normalized_ips.items():
        try:
            # Check if exists
            cursor.execute("SELECT ip FROM servers WHERE ip = ?", (normalized_ip,))
            exists = cursor.fetchone()
            
            if exists:
                # Update alternates if new ones found
                if alternates:
                    cursor.execute("SELECT alternate_ips FROM servers WHERE ip = ?", (normalized_ip,))
                    current = cursor.fetchone()[0]
                    if current:
                        existing_alts = [a.strip() for a in current.split(',')]
                    else:
                        existing_alts = []
                    
                    # Merge alternates
                    all_alts = list(set(existing_alts + alternates))
                    cursor.execute("""
                        UPDATE servers 
                        SET alternate_ips = ?, last_seen = ?
                        WHERE ip = ?
                    """, (', '.join(all_alts), datetime.now().isoformat(), normalized_ip))
                updated += 1
            else:
                # Insert new server directly
                alt_ips_str = ', '.join(alternates) if alternates else None
                cursor.execute("""
                    INSERT INTO servers (ip, country, isp, auth_mode, icon, alternate_ips, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (normalized_ip, 'Unknown', 'Unknown', 'UNKNOWN', None, alt_ips_str, datetime.now().isoformat()))
                added += 1
            
            if (added + updated) % 1000 == 0:
                print(f"  Progress: {added:,} added, {updated:,} updated")
                conn.commit()
        
        except Exception as e:
            print(f"❌ Error importing {normalized_ip}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Import complete!")
    print(f"   Added: {added:,} new servers")
    print(f"   Updated: {updated:,} existing servers")
    print(f"   Total in DB: {added + updated:,}")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    import glob
    
    # Find most recent scraped file
    files = glob.glob("data/minecraft_server_list_300pages_*.txt")
    if files:
        latest = max(files, key=os.path.getctime)
        print(f"📁 Using: {latest}")
        import_scraped_servers(latest)
    else:
        print("❌ No scraped files found in data/")
        print("   Run scrape_300_pages.py first")
