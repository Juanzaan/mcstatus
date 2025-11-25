"""
Add popular/known Minecraft servers to database.
Sources: Reddit, forums, top server lists.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import database as db
import sqlite3
from datetime import datetime

# List of popular servers with known variants
POPULAR_SERVERS = [
    # Hypixel Network
    {
        'main': 'mc.hypixel.net',
        'variants': ['hypixel.net', 'play.hypixel.net', 'HYPIXEL.NET', 'Hypixel.net']
    },
    # Mineplex
    {
        'main': 'us.mineplex.com',
        'variants': ['mineplex.com', 'eu.mineplex.com', 'Mineplex.com']
    },
    # CubeCraft
    {
        'main': 'play.cubecraft.net',
        'variants': ['cubecraft.net', 'CubeCraft.net']
    },
    # The Hive
    {
        'main': 'play.hivemc.com',
        'variants': ['hivemc.com', 'HiveMC.com']
    },
    # Minehut
    {
        'main': 'minehut.com',
        'variants': ['play.minehut.com', 'Minehut.com']
    },
    # Universocraft (Spanish)
    {
        'main': 'universocraft.com',
        'variants': ['play.universocraft.com', 'mc.universocraft.com', 'UniversoCraft.com']
    },
    # 2b2t (Anarchy)
    {
        'main': '2b2t.org',
        'variants': ['connect.2b2t.org', '2B2T.org']
    },
    # Wynncraft (RPG)
    {
        'main': 'play.wynncraft.com',
        'variants': ['wynncraft.com', 'WynnCraft.com']
    },
    # Pixelmon servers
    {
        'main': 'play.pixelmonrealms.com',
        'variants': ['pixelmonrealms.com']
    },
    # PvP Legacy
    {
        'main': 'pvplegacy.net',
        'variants': ['play.pvplegacy.net', 'PvPLegacy.net']
    },
    # BlocksMC
    {
        'main': 'blocksmc.com',
        'variants': ['play.blocksmc.com', 'BlocksMC.com']
    },
    # JartexNetwork
    {
        'main': 'jartexnetwork.com',
        'variants': ['play.jartexnetwork.com', 'JartexNetwork.com']
    },
    # PikaNetwork
    {
        'main': 'pika-network.net',
        'variants': ['play.pika-network.net', 'pikanetwork.net']
    },
    # VeltPvP
    {
        'main': 'veltpvp.com',
        'variants': ['play.veltpvp.com', 'VeltPvP.com']
    },
    # ManaCube
    {
        'main': 'manacube.com',
        'variants': ['play.manacube.com', 'ManaCube.com']
    },
    # ExtremeCraft (Spanish)
    {
        'main': 'extremecraft.net',
        'variants': ['play.extremecraft.net', 'ExtremeCraft.net']
    },
    # LemonCloud
    {
        'main': 'lemoncloud.net',
        'variants': ['play.lemoncloud.net', 'LemonCloud.net']
    },
    # MineLC (Español)
    {
        'main': 'minelc.net',
        'variants': ['play.minelc.net', 'MineLC.net']
    },
    # CraftLandia (BR)
    {
        'main': 'craftlandia.com.br',
        'variants': ['play.craftlandia.com.br']
    },
    # RedeSimple (BR)
    {
        'main': 'redesimple.net',
        'variants': ['play.redesimple.net', 'RedeSimple.net']
    },
]

def add_popular_servers():
    """Add popular servers with their variants to database"""
    print(f"\n{'='*70}")
    print(" ADDING POPULAR MINECRAFT SERVERS")
    print(f"{'='*70}\n")
    
    conn = sqlite3.connect(db.DB_FILE)
    cursor = conn.cursor()
    
    added = 0
    updated = 0
    
    for server_info in POPULAR_SERVERS:
        main_ip = db.normalize_server_address(server_info['main'])
        variants = server_info['variants']
        
        # Normalize variants
        normalized_variants = []
        for v in variants:
            normalized_v = db.normalize_server_address(v)
            if normalized_v != main_ip:  # Don't include if it normalizes to main
                normalized_variants.append(v)
        
        try:
            # Check if exists
            cursor.execute("SELECT ip, alternate_ips FROM servers WHERE ip = ?", (main_ip,))
            existing = cursor.fetchone()
            
            if existing:
                # Merge with existing alternates
                current_alts = existing[1].split(', ') if existing[1] else []
                all_alts = list(set(current_alts + normalized_variants))
                
                cursor.execute("""
                    UPDATE servers 
                    SET alternate_ips = ?, last_seen = ?
                    WHERE ip = ?
                """, (', '.join(all_alts), datetime.now().isoformat(), main_ip))
                
                print(f"✅ Updated {main_ip}: {len(all_alts)} alternates")
                updated += 1
            else:
                # Insert new
                alt_ips_str = ', '.join(normalized_variants) if normalized_variants else None
                
                cursor.execute("""
                    INSERT INTO servers (ip, country, isp, auth_mode, icon, alternate_ips, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (main_ip, 'Unknown', 'Unknown', 'UNKNOWN', None, alt_ips_str, datetime.now().isoformat()))
                
                print(f"➕ Added {main_ip}: {len(normalized_variants)} alternates")
                added += 1
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error with {main_ip}: {e}")
            continue
    
    conn.close()
    
    print(f"\n✅ Complete!")
    print(f"   Added: {added} new servers")
    print(f"   Updated: {updated} existing servers")
    print(f"   Total processed: {len(POPULAR_SERVERS)}")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    add_popular_servers()
    print("\n🔄 Now run scan_and_verify.py to update their status!")
