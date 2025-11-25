import json
from pathlib import Path

# Load cloudflare IPs
cloudflare_path = Path('data/cloudflare_bypass_ips.txt')
with open(cloudflare_path, 'r') as f:
    cloudflare_ips = set([line.strip() for line in f if line.strip()])

# Load unified servers
unified_path = Path('data/unified_servers.json')
with open(unified_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract all IPs
all_servers = data.get('premium', []) + data.get('non_premium', []) + data.get('offline', [])
unified_ips = set([s['ip'] for s in all_servers])

# Combine all unique IPs
all_ips = cloudflare_ips | unified_ips

print(f"📊 IP Sources:")
print(f"  Cloudflare IPs: {len(cloudflare_ips)}")
print(f"  Unified IPs: {len(unified_ips)}")
print(f"  Combined unique: {len(all_ips)}")

# Save to file for scanning
output_path = Path('data/all_ips_for_scan.txt')
with open(output_path, 'w') as f:
    for ip in sorted(all_ips):
        f.write(f"{ip}\n")

print(f"\n✅ Saved {len(all_ips)} IPs to {output_path}")
