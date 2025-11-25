import json
from pathlib import Path
from collections import Counter

# Load unified servers
unified_path = Path('data/unified_servers.json')
with open(unified_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count servers by category
premium = data.get('premium', [])
non_premium = data.get('non_premium', [])
offline = data.get('offline', [])

print(f"📊 Current State:")
print(f"  Premium: {len(premium)}")
print(f"  Non-Premium: {len(non_premium)}")
print(f"  Offline: {len(offline)}")
print(f"  Total: {len(premium) + len(non_premium) + len(offline)}")

# Check for duplicates
all_servers = premium + non_premium + offline
all_ips = [s['ip'] for s in all_servers]
ip_counts = Counter(all_ips)
duplicates = {ip: count for ip, count in ip_counts.items() if count > 1}

print(f"\n🔍 Duplicates Found: {len(duplicates)}")
for ip, count in duplicates.items():
    print(f"  {ip}: {count} times")

# Check Cloudflare IPs
cloudflare_ips_path = Path('data/cloudflare_bypass_ips.txt')
with open(cloudflare_ips_path, 'r') as f:
    cloudflare_ips = set([line.strip() for line in f if line.strip()])

print(f"\n📂 Cloudflare IPs: {len(cloudflare_ips)}")

# Missing IPs (in Cloudflare but not in unified)
unified_ip_set = set(all_ips)
missing_ips = cloudflare_ips - unified_ip_set

print(f"\n❌ Missing IPs (in Cloudflare but not in unified): {len(missing_ips)}")
print(f"  First 10: {list(missing_ips)[:10]}")

# Save missing IPs to file
with open('data/missing_ips.txt', 'w') as f:
    for ip in sorted(missing_ips):
        f.write(f"{ip}\n")

print(f"\n✅ Saved {len(missing_ips)} missing IPs to data/missing_ips.txt")
