"""Deduplication analysis utility.

Provides two modes:
  * Default (no flags) – runs the original find_duplicates logic.
  * --tld – also runs the TLD‑variant detection (original find_tld_duplicates).

Usage:
    python dedup_analysis.py [--tld]
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict
import re

def load_data():
    unified_path = Path('data/unified_servers.json')
    with open(unified_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_duplicates(data):
    all_servers = data.get('premium', []) + data.get('non_premium', []) + data.get('offline', [])
    print(f"📊 Total servers: {len(all_servers)}")
    domain_groups = defaultdict(list)
    for server in all_servers:
        ip = server['ip']
        domain = ip.split(':')[0] if ':' in ip else ip
        domain_groups[domain].append(ip)
    duplicates = {d: ips for d, ips in domain_groups.items() if len(ips) > 1}
    print(f"\n🔍 Potential duplicates found: {len(duplicates)}")
    for i, (domain, ips) in enumerate(list(duplicates.items())[:20], 1):
        print(f"\n{i}. Domain: {domain}\n   Variants: {', '.join(ips)}")
    total_dup = sum(len(ips) - 1 for ips in duplicates.values())
    print(f"\n📈 Total duplicate IPs that could be merged: {total_dup}")
    print(f"   After merge: {len(all_servers)} → {len(all_servers) - total_dup}")

def get_base_domain(ip):
    # Remove port
    domain = ip.split(':')[0] if ':' in ip else ip
    # Skip raw IPs
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
        return None
    # Remove common prefixes
    for prefix in ['mc.', 'play.', 'hub.', 'lobby.', 'join.', 'go.', 'mp.', 'server.', 'srv.']:
        if domain.lower().startswith(prefix):
            domain = domain[len(prefix):]
            break
    # Remove TLD
    parts = domain.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[:-1]).lower()
    return domain.lower()

def find_tld_variants(data):
    all_servers = data.get('premium', []) + data.get('non_premium', []) + data.get('offline', [])
    base_groups = defaultdict(list)
    for server in all_servers:
        base = get_base_domain(server['ip'])
        if base:
            base_groups[base].append(server)
    tld_dups = {b: s for b, s in base_groups.items() if len(s) > 1}
    print(f"\n🔍 Domain TLD variants found: {len(tld_dups)}")
    for i, (base, servers) in enumerate(list(tld_dups.items())[:25], 1):
        print(f"\n{i}. Base domain: {base}")
        for s in servers:
            premium = '👑 PREMIUM' if s.get('premium') else ''
            print(f"   - {s['ip']} ({s.get('name','')}) - {s.get('online',0)} players {premium}")
    total = sum(len(s)-1 for s in tld_dups.values())
    print(f"\n📈 Total TLD variant IPs that could be merged: {total}")
    print(f"   After merge: {len(all_servers)} → {len(all_servers) - total}")

def main():
    parser = argparse.ArgumentParser(description='Deduplication analysis')
    parser.add_argument('--tld', action='store_true', help='Run TLD variant analysis as well')
    args = parser.parse_args()
    data = load_data()
    find_duplicates(data)
    if args.tld:
        find_tld_variants(data)

if __name__ == '__main__':
    main()
