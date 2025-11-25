#!/usr/bin/env python3
"""
Comprehensive Database Deduplication Script
-------------------------------------------
Removes duplicate server entries from SQLite database using
normalization and merging strategies.

Usage:
    python scripts/deduplicate_database.py [--dry-run] [--backup]
"""

import sqlite3
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_FILE = os.path.join("data", "servers.db")


def normalize_server_address(address: str) -> str:
    """
    Normalize server address to canonical form.
    
    Rules:
    - Lowercase hostname
    - Remove default port :25565
    - Strip whitespace
    - Remove protocol prefixes
    """
    if not address:
        return address
    
    # Strip whitespace
    address = address.strip()
    
    # Remove protocol prefixes
    for prefix in ['minecraft://', 'mc://', 'http://', 'https://']:
        if address.lower().startswith(prefix):
            address = address[len(prefix):]
    
    # Lowercase (preserve port if present)
    if ':' in address:
        host, port = address.rsplit(':', 1)
        address = f"{host.lower()}:{port}"
    else:
        address = address.lower()
    
    # Remove default port :25565
    if address.endswith(':25565'):
        address = address[:-6]
    
    return address


def backup_database():
    """Create a backup of the database before deduplication."""
    if not os.path.exists(DB_FILE):
        print(f"❌ Database not found: {DB_FILE}")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{DB_FILE}.backup_{timestamp}"
    
    import shutil
    shutil.copy2(DB_FILE, backup_file)
    print(f"✅ Backup created: {backup_file}")
    return True


def identify_duplicates(conn: sqlite3.Connection) -> List[Dict]:
    """
    Identify all duplicate entries.
    
    Returns list of duplicate groups with:
    - normalized_ip: The canonical form
    - ips: List of all variant IPs
    - keep_ip: The IP to keep (most recent)
    - delete_ips: IPs to delete
    """
    cursor = conn.cursor()
    
    # Find all duplicate groups
    cursor.execute("""
        WITH normalized AS (
            SELECT 
                ip,
                LOWER(TRIM(REPLACE(ip, ':25565', ''))) as normalized_ip,
                last_seen
            FROM servers
        )
        SELECT 
            normalized_ip,
            GROUP_CONCAT(ip, '|') as ips,
            GROUP_CONCAT(last_seen, '|') as last_seens,
            COUNT(*) as count
        FROM normalized
        GROUP BY normalized_ip
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """)
    
    duplicate_groups = []
    for row in cursor.fetchall():
        norm_ip, ips_str, last_seens_str, count = row
        ips = ips_str.split('|')
        last_seens = last_seens_str.split('|')
        
        # Find the IP with most recent last_seen
        ip_data = list(zip(ips, last_seens))
        ip_data.sort(key=lambda x: x[1], reverse=True)
        
        keep_ip = ip_data[0][0]
        delete_ips = [ip for ip, _ in ip_data[1:]]
        
        duplicate_groups.append({
            'normalized_ip': norm_ip,
            'ips': ips,
            'keep_ip': keep_ip,
            'delete_ips': delete_ips,
            'count': count
        })
    
    return duplicate_groups


def merge_and_delete_duplicates(conn: sqlite3.Connection, duplicate_groups: List[Dict], dry_run: bool = False):
    """
    Merge duplicate entries and delete redundant ones.
    
    Strategy:
    1. Reassign all snapshots to keep_ip
    2. Update keep_ip to normalized form
    3. Delete redundant server entries
    """
    cursor = conn.cursor()
    total_deleted = 0
    
    for group in duplicate_groups:
        keep_ip = group['keep_ip']
        delete_ips = group['delete_ips']
        norm_ip = group['normalized_ip']
        
        print(f"\n📦 Group: {norm_ip}")
        print(f"   Keeping: {keep_ip}")
        print(f"   Deleting: {', '.join(delete_ips)}")
        
        if dry_run:
            continue
        
        try:
            # Step 1: Reassign snapshots from delete_ips to keep_ip
            for del_ip in delete_ips:
                cursor.execute("""
                    UPDATE server_snapshots 
                    SET ip = ? 
                    WHERE ip = ?
                """, (keep_ip, del_ip))
                print(f"   ↳ Reassigned {cursor.rowcount} snapshots from {del_ip}")
            
            # Step 2: Delete redundant server entries
            for del_ip in delete_ips:
                cursor.execute("DELETE FROM servers WHERE ip = ?", (del_ip,))
                total_deleted += cursor.rowcount
            
           # Step 3: Normalize the kept IP
            if keep_ip != norm_ip:
                # Check if norm_ip already exists (shouldn't happen, but safety check)
                cursor.execute("SELECT 1 FROM servers WHERE ip = ?", (norm_ip,))
                if cursor.fetchone():
                    print(f"   ⚠️  Normalized IP {norm_ip} already exists, skipping normalization")
                else:
                    cursor.execute("UPDATE servers SET ip = ? WHERE ip = ?", (norm_ip, keep_ip))
                    cursor.execute("UPDATE server_snapshots SET ip = ? WHERE ip = ?", (norm_ip, keep_ip))
                    print(f"   ↳ Normalized {keep_ip} -> {norm_ip}")
            
            conn.commit()
            
        except Exception as e:
            print(f"   ❌ Error processing group: {e}")
            conn.rollback()
    
    return total_deleted


def main():
    parser = argparse.ArgumentParser(description="Deduplicate SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--backup", action="store_true", help="Create backup before deduplication")
    args = parser.parse_args()
    
    print("=== Database Deduplication ===\n")
    
    if args.backup and not args.dry_run:
        if not backup_database():
            print("Backup failed, aborting.")
            return
    
    # Connect to database
    conn = sqlite3.connect(DB_FILE)
    
    # Identify duplicates
    print("🔍 Identifying duplicates...")
    duplicate_groups = identify_duplicates(conn)
    
    if not duplicate_groups:
        print("✅ No duplicates found!")
        conn.close()
        return
    
    print(f"\n📊 Found {len(duplicate_groups)} duplicate groups")
    total_duplicates = sum(group['count'] - 1 for group in duplicate_groups)
    print(f"   Total duplicate entries: {total_duplicates}")
    
    if args.dry_run:
        print("\n🔬 DRY RUN MODE - No changes will be made\n")
    
    # Merge and delete
    print("\n🔧 Processing duplicates...")
    deleted_count = merge_and_delete_duplicates(conn, duplicate_groups, dry_run=args.dry_run)
    
    if not args.dry_run:
        print(f"\n✅ Deduplication complete!")
        print(f"   Deleted {deleted_count} duplicate entries")
        
        # Verify
        print("\n🔍 Verifying...")
        remaining_dupes = identify_duplicates(conn)
        if remaining_dupes:
            print(f"⚠️  Warning: {len(remaining_dupes)} duplicate groups still remain")
        else:
            print("✅ No duplicates remaining")
    
    conn.close()


if __name__ == "__main__":
    main()
