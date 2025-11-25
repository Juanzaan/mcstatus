"""
Priority scanner module for high-value servers.
"""
import asyncio
from datetime import datetime
from mcstatus import JavaServer
from core import database as db
import logging

logger = logging.getLogger(__name__)

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

async def scan_single_server(ip, scan_id):
    try:
        # Use longer timeout for popular servers
        server = await JavaServer.async_lookup(ip, timeout=10)
        status = await server.async_status()
        
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
            0, 0, 0, 0
        ))
        
        # Update server last_seen
        c.execute("UPDATE servers SET last_seen = ? WHERE ip = ?", (datetime.now().isoformat(), ip))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.warning(f"Priority scan failed for {ip}: {e}")
        return False

async def run_priority_scan():
    """Run priority scan for all popular servers."""
    logger.info("🚀 Starting priority scan for popular servers...")
    
    # Get or create scan ID
    conn = db.sqlite3.connect(db.DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO scans (timestamp) VALUES (?)", (datetime.now().isoformat(),))
    scan_id = c.lastrowid
    conn.commit()
    conn.close()
    
    success = 0
    tasks = [scan_single_server(ip, scan_id) for ip in POPULAR_SERVERS]
    results = await asyncio.gather(*tasks)
    
    success = sum(1 for r in results if r)
    logger.info(f"✅ Priority scan complete: {success}/{len(POPULAR_SERVERS)} updated")
