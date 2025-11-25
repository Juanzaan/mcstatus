"""
Manual consolidation of Minehut cluster under minehut.gg.
Fixes historical data issue where minehut.gg never resolved DNS.
"""
import sqlite3

DB_FILE = 'data/servers.db'

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("🔧 Starting Minehut Cluster Consolidation...")
print("=" * 60)

try:
    # Step 1: Get current state
    cursor.execute("SELECT COUNT(*) FROM server_aliases WHERE canonical_ip = 'cookiescafe.minehut.gg'")
    old_count = cursor.fetchone()[0]
    print(f"\n📊 Current state: {old_count} aliases pointing to cookiescafe.minehut.gg")
    
    # Step 2: Update all existing aliases to point to minehut.gg
    cursor.execute("""
        UPDATE server_aliases
        SET canonical_ip = 'minehut.gg'
        WHERE canonical_ip = 'cookiescafe.minehut.gg'
    """)
    updated_aliases = cursor.rowcount
    print(f"✅ Step 1: Updated {updated_aliases} aliases to point to minehut.gg")
    
    # Step 3: Add cookiescafe.minehut.gg as an alias itself
    cursor.execute("""
        INSERT OR IGNORE INTO server_aliases (alias_ip, canonical_ip, detection_method, confidence_score)
        VALUES ('cookiescafe.minehut.gg', 'minehut.gg', 'manual_consolidation', 1.0)
    """)
    print(f"✅ Step 2: Added cookiescafe.minehut.gg as alias")
    
    # Step 4: Mark cookiescafe.minehut.gg as non-canonical
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 0, canonical_id = 'minehut.gg'
        WHERE ip = 'cookiescafe.minehut.gg'
    """)
    print(f"✅ Step 3: Marked cookiescafe.minehut.gg as alias (is_canonical=0)")
    
    # Step 5: Ensure minehut.gg is canonical
    cursor.execute("""
        UPDATE servers
        SET is_canonical = 1, canonical_id = NULL
        WHERE ip = 'minehut.gg'
    """)
    print(f"✅ Step 4: Confirmed minehut.gg as canonical (is_canonical=1)")
    
    # Commit changes
    conn.commit()
    
    # Step 6: Verify final state
    print("\n" + "=" * 60)
    print("📋 VERIFICATION:")
    
    cursor.execute("SELECT COUNT(*) FROM server_aliases WHERE canonical_ip = 'minehut.gg'")
    new_count = cursor.fetchone()[0]
    print(f"  ✓ Aliases pointing to minehut.gg: {new_count}")
    
    cursor.execute("SELECT is_canonical FROM servers WHERE ip = 'minehut.gg'")
    minehut_canonical = cursor.fetchone()[0]
    print(f"  ✓ minehut.gg is_canonical: {minehut_canonical}")
    
    cursor.execute("SELECT is_canonical FROM servers WHERE ip = 'cookiescafe.minehut.gg'")
    cookiescafe_canonical = cursor.fetchone()[0]
    print(f"  ✓ cookiescafe.minehut.gg is_canonical: {cookiescafe_canonical}")
    
    cursor.execute("""
        SELECT alias_ip FROM server_aliases 
        WHERE canonical_ip = 'minehut.gg'
        ORDER BY alias_ip
    """)
    all_aliases = cursor.fetchall()
    print(f"\n  📝 All {len(all_aliases)} Minehut aliases:")
    for (alias,) in all_aliases:
        print(f"     - {alias}")
    
    print("\n" + "=" * 60)
    print("🎉 Minehut Cluster Consolidation COMPLETE!")
    print(f"   Result: {new_count} aliases → minehut.gg (canonical)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    conn.rollback()
    raise
finally:
    conn.close()
