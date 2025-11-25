import json
from pathlib import Path
from collections import defaultdict
import re

# Load unified servers
unified_path = Path('data/unified_servers.json')
with open(unified_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Collect all servers
all_servers = data.get('premium', []) + data.get('non_premium', []) + data.get('offline', [])

print(f"📊 Total servers: {len(all_servers)}")

# Extract base domain (remove TLD and common prefixes)
def get_base_domain(ip):
    # Remove port
    if ':' in ip:
        domain = ip.split(':')[0]
    else:
        domain = ip
    
    # Skip if it's a raw IP address
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
        return None
    
    # Remove common prefixes
    for prefix in ['mc.', 'play.', 'hub.', 'lobby.', 'join.', 'go.', 'mp.', 'server.', 'srv.']:
        if domain.lower().startswith(prefix):
            domain = domain[len(prefix):]
    
    # Remove TLD (.com, .net, .org, etc.)
    parts = domain.split('.')
    if len(parts) >= 2:
        # Take everything except the last part (TLD)
        base = '.'.join(parts[:-1])
        return base.lower()
    
    return domain.lower()

# Group by base domain
base_domain_groups = defaultdict(list)

for server in all_servers:
    ip = server['ip']
    base = get_base_domain(ip)
    
    if base:
        base_domain_groups[base].append({
            'ip': ip,
            'name': server.get('name', 'Unknown'),
            'online': server.get('online', 0),
            'category': server.get('premium', False)
        })

# Find potential duplicates (same base, different TLDs)
tld_duplicates = {base: servers for base, servers in base_domain_groups.items() if len(servers) > 1}

print(f"\n🔍 Domain TLD variants found: {len(tld_duplicates)}")
print(f"\nShowing examples:")
print("=" * 70)

for i, (base, servers) in enumerate(list(tld_duplicates.items())[:25], 1):
    print(f"\n{i}. Base domain: {base}")
    for s in servers:
        premium = "👑 PREMIUM" if s['category'] else ""
        print(f"   - {s['ip']} ({s['name']}) - {s['online']} players {premium}")

# Calculate impact
total_tld_variants = sum(len(servers) - 1 for servers in tld_duplicates.values())
print(f"\n📈 Total TLD variant IPs that could be merged: {total_tld_variants}")
print(f"   Current: {len(all_servers)} → After merge: {len(all_servers) - total_tld_variants}")
