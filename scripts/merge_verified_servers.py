#!/usr/bin/env python3
"""
Merge verified_servers.json into unified_servers.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core import config

def merge_servers():
    # Load both files
    verified_file = config.DATA_DIR / 'verified_servers.json'
    unified_file = config.UNIFIED_SERVERS_FILE
    
    print("Loading verified_servers.json...")
    with open(verified_file, 'r', encoding='utf-8') as f:
        verified = json.load(f)
    
    print("Loading unified_servers.json...")
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified = json.load(f)
    
    # Create IP sets from unified
    unified_ips = set()
    for category in ['premium', 'non_premium', 'offline']:
        for server in unified.get(category, []):
            unified_ips.add(server['ip'])
    
    # Find new servers in verified
    new_servers = []
    for server in verified:
        if server['ip'] not in unified_ips:
            new_servers.append(server)
    
    print(f"\nFound {len(new_servers)} new servers in verified_servers.json")
    
    if len(new_servers) == 0:
        print("✅ All verified servers are already in unified_servers.json")
        return
    
    # Categorize new servers
    for server in new_servers:
        if server.get('status') == 'offline':
            unified.setdefault('offline', []).append(server)
        elif server.get('premium'):
            unified.setdefault('premium', []).append(server)
        else:
            unified.setdefault('non_premium', []).append(server)
    
    # Backup original
    backup_file = unified_file.parent / f"unified_backup_pre_merge_{Path(__file__).stem}.json"
    print(f"\nCreating backup: {backup_file.name}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(unified, f, indent=2)
    
    # Save merged
    print("Saving merged unified_servers.json...")
    with open(unified_file, 'w', encoding='utf-8') as f:
        json.dump(unified, f, indent=2)
    
    # Print stats
    total = sum(len(unified.get(k, [])) for k in ['premium', 'non_premium', 'offline'])
    print(f"\n✅ Merge complete!")
    print(f"   Total servers: {total}")
    print(f"   Premium: {len(unified.get('premium', []))}")
    print(f"   Non-Premium: {len(unified.get('non_premium', []))}")
    print(f"   Offline: {len(unified.get('offline', []))}")

if __name__ == "__main__":
    merge_servers()
