import requests
import json

# Test API /servers endpoint
response = requests.get('http://localhost:5000/api/servers', params={'limit': 10})
data = response.json()

print(f"API /servers returns: {len(data.get('servers', []))} servers")
print(f"Pagination total_items: {data.get('pagination', {}).get('total_items')}")
print(f"\nFirst 5 servers:")
for s in data.get('servers', [])[:5]:
    print(f"  {s.get('ip'):35} is_canonical={s.get('is_canonical')}")

# Check if any Minehut aliases are in the response
minehut_servers = [s for s in data.get('servers', []) if 'minehut.gg' in s.get('ip', '').lower()]
print(f"\nMinehut servers in first batch: {len(minehut_servers)}")
for s in minehut_servers:
    print(f"  {s.get('ip'):35} is_canonical={s.get('is_canonical')}")
