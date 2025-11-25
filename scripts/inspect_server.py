import json
from pathlib import Path


data_path = Path('data/unified_servers.json')

try:
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        # Search in all categories
        found = False
        for category in ['premium', 'non_premium', 'offline']:
            for server in data.get(category, []):
                if 'hypixel' in server.get('ip', '').lower() or 'hypixel' in server.get('name', '').lower():
                    print(f"Found in {category}:")
                    print(json.dumps(server, indent=2))
                    found = True
                    
        if not found:
            print("Hypixel not found in any category.")

except Exception as e:
    print(f"Error: {e}")
