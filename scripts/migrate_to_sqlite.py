#!/usr/bin/env python3
"""
SQLite Migration Script
-----------------------
Migrates data from unified_servers.json to SQLite database.

Usage:
    python scripts/migrate_to_sqlite.py [--dry-run]
"""
import sys
import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import database as db
from core import config

def backup_json():
    """Create backup of JSON file before migration"""
    json_file = config.UNIFIED_SERVERS_FILE
    if not json_file.exists():
        print(f"⚠️  No JSON file found at {json_file}")
        return False
        
    backup_file = json_file.parent / f"unified_servers_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy2(json_file, backup_file)
    print(f"✅ Backup created: {backup_file}")
    return True

def migrate_data(dry_run=False):
    """Migrate JSON data to SQLite"""
    json_file = config.UNIFIED_SERVERS_FILE
    
    if not json_file.exists():
        print(f"❌ JSON file not found: {json_file}")
        return False
        
    # Load JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count servers
    total_servers = 0
    for category in ['premium', 'non_premium', 'offline']:
        total_servers += len(data.get(category, []))
    
    print(f"\n📊 Found {total_servers} servers to migrate")
    
    if dry_run:
        print("🔍 DRY RUN - No data will be written")
        return True
    
    # Initialize database
    print("\n🔧 Initializing database...")
    db.init_db()
    
    # Create a scan for the migration
    scan_id = db.create_scan()
    print(f"✅ Created migration scan with ID: {scan_id}")
    
    # Migrate servers
    migrated = 0
    errors = 0
    
    for category in ['premium', 'non_premium', 'offline']:
        servers = data.get(category, [])
        print(f"\n📦 Migrating {len(servers)} servers from '{category}'...")
        
        for server in servers:
            try:
                # Map JSON format to database format
                # Infer auth_mode from category if not present or UNKNOWN
                auth_mode = server.get('auth_mode', '').upper()
                if not auth_mode or auth_mode == 'UNKNOWN':
                    if category == 'premium':
                        auth_mode = 'PREMIUM'
                    elif category == 'non_premium':
                        auth_mode = 'NO-PREMIUM'
                    else:  # offline
                        # For offline, check if IP suggests premium (has auth check)
                        auth_mode = 'UNKNOWN'
                
                server_data = {
                    'ip': server.get('ip', 'unknown'),
                    'country': server.get('country', 'Unknown'),
                    'isp': server.get('isp', 'Unknown'),
                    'auth_mode': auth_mode,
                    'version': server.get('version', 'Unknown'),
                    'online': server.get('online', 0),
                    'max': server.get('max') or server.get('max_players', 0),
                    'sample_size': server.get('sample_size', 0),
                    'premium': server.get('premium_count', 0),
                    'cracked': server.get('cracked_count', 0),
                    'new_players': server.get('new_players', 0),
                    'icon': server.get('icon')
                }
                
                db.save_server_data(scan_id, server_data)
                migrated += 1
                
                if migrated % 100 == 0:
                    print(f"  ✓ Migrated {migrated}/{total_servers}")
                    
            except Exception as e:
                print(f"  ❌ Error migrating {server.get('ip')}: {e}")
                errors += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated}")
    print(f"   Errors: {errors}")
    print(f"   Database: {db.DB_FILE}")
    
    return True

def main():
    dry_run = '--dry-run' in sys.argv
    
    print("="*50)
    print("  SQLite Migration Tool")
    print("="*50)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    
    # Backup JSON
    if not dry_run:
        if not backup_json():
            print("❌ Failed to create backup. Aborting.")
            return 1
    
    # Migrate
    if migrate_data(dry_run):
        print("\n✅ Migration successful!")
        if not dry_run:
            print("\n💡 Next steps:")
            print("   1. Test the database: python -c 'from core import database; print(database.get_stats())'")
            print("   2. Update core/api.py to use database instead of JSON")
            print("   3. Update scanner to write to database")
        return 0
    else:
        print("\n❌ Migration failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
