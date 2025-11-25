"""
Complete Minehut consolidation including .minehut.com domains
"""
import sqlite3

DB_FILE = 'data/servers.db'

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("🔧 Complete Minehut Consolidation (.com + .gg)")
print("=" * 70)

try:
    # Step 1: Find all Minehut-related servers
    cursor.execute("""
        SELECT ip, is_canonical 
        FROM servers 
        WHERE (ip LIKE '%minehut.gg%' OR ip LIKE '%minehut.com%')
        ORDER BY ip
    """)
    all_minehut = cursor.fetchall()
    
    print(f"\n📊 All Minehut-related servers ({len(all_minehut)}):")
    for ip, is_canonical in all_minehut:
        status = "CANONICAL" if is_canonical == 1 else "ALIAS"
        print(f"  {ip:40} → {status}")
    
    # Determine which should be canonical: minehut.gg vs minehut.com
    # minehut.gg has fewer characters (10) than minehut.com (11)
    # Both have 1 dot, so by length: minehut.gg wins
    canonical = "minehut.gg"
    
    print(f"\n📌 Selected canonical: {canonical}")
    
    # Step 2: Mark ALL Minehut servers as aliases (except canonical)
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 0, canonical_id = ?
        WHERE (ip LIKE '%minehut.gg%' OR ip LIKE '%minehut.com%')
        AND ip != ?
    """, (canonical, canonical))
    updated = cursor.rowcount
    print(f"\n✅ Marked {updated} Minehuservers as aliases")
    
    # Step 3: Ensure canonical is set correctly
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 1, canonical_id = NULL
        WHERE ip = ?
    """, (canonical,))
    
    # Step 4: Add all to server_aliases
    cursor.execute("""
        INSERT OR IGNORE INTO server_aliases (alias_ip, canonical_ip, detection_method, confidence_score)
        SELECT ip, ?, 'complete_minehut_consolidation', 1.0
        FROM servers
        WHERE (ip LIKE '%minehut.gg%' OR ip LIKE '%minehut.com%')
        AND ip != ?
    """, (canonical, canonical))
    added = cursor.rowcount
    print(f"✅ Added {added} entries to server_aliases")
    
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT COUNT(*) FROM servers 
        WHERE (ip LIKE '%minehut.gg%' OR ip LIKE '%minehut.com%')
        AND is_canonical = 1
    """)
    final_canonical = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM servers 
        WHERE (ip LIKE '%minehut.gg%' OR ip LIKE '%minehut.com%')
        AND is_canonical = 0
    """)
    final_aliases = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM server_aliases 
        WHERE canonical_ip = ?
    """, (canonical,))
    alias_entries = cursor.fetchone()[0]
    
    # Global counts
    cursor.execute("SELECT COUNT(*) FROM servers WHERE is_canonical = 1")
    global_canonical = cursor.fetchone()[0]
    
    print(f"\n" + "=" * 70)
    print(f"📋 FINAL STATE:")
    print(f"  Minehut canonical servers: {final_canonical} (should be 1)")
    print(f"  Minehut aliases: {final_aliases}")
    print(f"  server_aliases entries: {alias_entries}")
    print(f"\n  GLOBAL canonical count: {global_canonical}")
    print(f"  Expected dashboard count: {global_canonical}")
    print("=" * 70)
    print("🎉 Complete Minehut consolidation DONE!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
