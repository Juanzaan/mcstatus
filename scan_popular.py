"""
Scan specific popular servers that were just added.
"""
import sys
sys.path.append('.')

from core import database as db
import asyncio

# Popular servers to verify
SERVERS_TO_SCAN = [
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
]

if __name__ == "__main__":
    print("\n🎯 Scanning popular servers...")
    print(f"   Targets: {len(SERVERS_TO_SCAN)} servers\n")
    
    # Create scan
    conn = db.sqlite3.connect(db.DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scans (started_at) VALUES (?)", (db.datetime.now().isoformat(),))
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Import scanner module
    import scripts.scan_and_verify as scanner
    
    # Scan each server
    async def scan_all():
        for sv in SERVERS_TO_SCAN:
            result = await scanner.scan_server(sv, scan_id)
            if result:
                scanner.save_buffer([result], scan_id)
                status = "✅" if result['online'] > 0 else "⚠️"
                print(f"{status} {sv}: {result['online']} players")
            else:
                print(f"❌ {sv}: offline/error")
    
    asyncio.run(scan_all())
    print("\n✅ Scan complete!")
