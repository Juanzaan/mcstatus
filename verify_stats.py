import requests

try:
    r = requests.get('http://localhost:5000/api/stats')
    data = r.json()
    stats = data['stats']
    
    print(f"Total Servers: {stats['total_servers']}")
    print(f"Premium: {stats['premium_count']}")
    print(f"Non-Premium: {stats['cracked_count']}")
    print(f"Sum: {stats['premium_count'] + stats['cracked_count']}")
    print(f"Match: {'✅ YES' if stats['total_servers'] == stats['premium_count'] + stats['cracked_count'] else '❌ NO'}")
    
except Exception as e:
    print(f"Error: {e}")
