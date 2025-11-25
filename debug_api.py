import requests
import json

try:
    print("Querying API...")
    r = requests.get('http://localhost:5000/api/servers?page=1&limit=50&category=all')
    data = r.json()
    
    print(f"Success: {data.get('success')}")
    print(f"Pagination: {data.get('pagination')}")
    
    servers = data.get('servers', [])
    print(f"Servers Returned: {len(servers)}")
    
    if servers:
        print("First 3 servers:")
        for s in servers[:3]:
            print(f"- {s.get('ip')} (Online: {s.get('online')})")
            
except Exception as e:
    print(f"Error: {e}")
