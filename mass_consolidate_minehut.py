"""
Mass consolidation of ALL Minehut subdomains under minehut.gg.
This fixes the issue where 8+ Minehut servers are still showing as canonical.
"""
import sqlite3

DB_FILE = 'data/servers.db'

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("🔧 Mass Minehut Consolidation - Complete Cleanup")
print("=" * 70)

try:
    # Step 1: Count current state
    cursor.execute("""
        SELECT COUNT(*) FROM servers 
        WHERE ip LIKE '%.minehut.gg%' AND is_canonical = 1
    """)
    current_canonical = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT ip FROM servers 
        WHERE ip LIKE '%.minehut.gg%' AND is_canonical = 1 
        AND ip != 'minehut.gg'
        ORDER BY ip
    """)
    subdomains_to_fix = cursor.fetchall()
    
    print(f"\n📊 Current State:")
    print(f"  Total Minehut with is_canonical=1: {current_canonical}")
    print(f"  Subdomains to mark as aliases: {len(subdomains_to_fix)}")
    
    if subdomains_to_fix:
        print(f"\n  List of subdomains that will become aliases:")
        for (ip,) in subdomains_to_fix[:10]:
            print(f"    - {ip}")
        if len(subdomains_to_fix) > 10:
            print(f"    ... and {len(subdomains_to_fix) - 10} more")
    
    # Step 2: Mark all subdomains as aliases
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 0, canonical_id = 'minehut.gg'
        WHERE ip LIKE '%.minehut.gg%' 
        AND ip != 'minehut.gg'
    """)
    updated_servers = cursor.rowcount
    print(f"\n✅ Step 1: Marked {updated_servers} Minehut subdomains as aliases")
    
    # Step 3: Add all to server_aliases table
    cursor.execute("""
        INSERT OR IGNORE INTO server_aliases (alias_ip, canonical_ip, detection_method, confidence_score)
        SELECT ip, 'minehut.gg', 'mass_consolidation', 1.0
        FROM servers
        WHERE ip LIKE '%.minehut.gg%' 
        AND ip != 'minehut.gg'
    """)
    new_aliases_added = cursor.rowcount
    print(f"✅ Step 2: Added {new_aliases_added} new entries to server_aliases")
    
    # Step 4: Ensure minehut.gg is canonical
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 1, canonical_id = NULL
        WHERE ip = 'minehut.gg'
    """)
    print(f"✅ Step 3: Confirmed minehut.gg as canonical")
    
    # Commit changes
    conn.commit()
    
    # Step 5: Verify final state
    print("\n" + "=" * 70)
    print("📋 VERIFICATION:")
    
    cursor.execute("""
        SELECT COUNT(*) FROM servers 
        WHERE ip LIKE '%.minehut.gg%' AND is_canonical = 1
    """)
    final_canonical = cursor.fetchone()[0]
    print(f"  ✓ Minehut servers with is_canonical=1: {final_canonical} (should be 1)")
    
    cursor.execute("""
        SELECT COUNT(*) FROM servers 
        WHERE ip LIKE '%.minehut.gg%' AND is_canonical = 0
    """)
    final_aliases = cursor.fetchone()[0]
    print(f"  ✓ Minehut aliases (is_canonical=0): {final_aliases}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM server_aliases 
        WHERE canonical_ip = 'minehut.gg'
    """)
    total_alias_entries = cursor.fetchone()[0]
    print(f"  ✓ Total entries in server_aliases for minehut.gg: {total_alias_entries}")
    
    # Global canonical count
    cursor.execute("SELECT COUNT(*) FROM servers WHERE is_canonical = 1")
    global_canonical = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM servers WHERE is_canonical = 0")
    global_aliases = cursor.fetchone()[0]
    
    print(f"\n📊 GLOBAL COUNTS:")
    print(f"  ✓ Total canonical servers: {global_canonical}")
    print(f"  ✓ Total aliases: {global_aliases}")
    print(f"  ✓ Grand total: {global_canonical + global_aliases}")
    
    print("\n" + "=" * 70)
    print("🎉 Mass Minehut Consolidation COMPLETE!")
    print(f"   Result: {final_aliases} Minehut aliases → minehut.gg (canonical)")
    print(f"   Expected dashboard count: {global_canonical}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
