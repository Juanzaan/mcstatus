"""
Priority scanner for popular servers.
Ensures high-value targets are always updated correctly.
"""
import sys
import os
import asyncio
from datetime import datetime
from mcstatus import JavaServer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import database as db

POPULAR_SERVERS = [
    'mc.hypixel.net',
    'minehut.com',
    'universocraft.com',
    'play.cubecraft.net',
    'play.hivemc.com',
    'us.mineplex.com',
    '2b2t.org',
    'play.wynncraft.com',
    'blocksmc.com',
    'jartexnetwork.com',
    'pika-network.net',
    'extremecraft.net',
    'lemoncloud.net',
    'minelc.net',
    'donutsmp.net',
    'play.donutsmp.net'
]

async def scan_priority_server(ip, scan_id):
    print(f"🔎 Scanning {ip}...", end='', flush=True)
    try:
        # Use longer timeout for popular servers
        server = await JavaServer.async_lookup(ip, timeout=10)
        status = await server.async_status()
        
        print(f" ✅ ONLINE ({status.players.online} players)")
        
        # Save result directly
        conn = db.sqlite3.connect(db.DB_FILE)
        c = conn.cursor()
        
        # Insert snapshot
        c.execute("""
            INSERT INTO server_snapshots 
            (scan_id, ip, version, online, max_players, sample_size, premium_count, cracked_count, new_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scan_id, 
            ip, 
            status.version.name, 
            status.players.online, 
            status.players.max,
            0, 0, 0, 0  # No player sampling for priority scan
        ))
        
        # Update server last_seen
        c.execute("UPDATE servers SET last_seen = ? WHERE ip = ?", (datetime.now().isoformat(), ip))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f" ❌ ERROR: {e}")
        return False

async def main():
    print(f"\n{'='*60}")
    print(" PRIORITY SERVER SCANNER")
    print(f"{'='*60}\n")
    
    # Get or create scan ID
    conn = db.sqlite3.connect(db.DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO scans (timestamp) VALUES (?)", (datetime.now().isoformat(),))
    scan_id = c.lastrowid
    conn.commit()
    conn.close()
    
    success = 0
    for ip in POPULAR_SERVERS:
        if await scan_priority_server(ip, scan_id):
            success += 1
            
    print(f"\n✅ Updated {success}/{len(POPULAR_SERVERS)} popular servers")

if __name__ == "__main__":
    asyncio.run(main())
