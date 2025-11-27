"""
Test script for Enterprise API
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    """Test root endpoint"""
    print("Testing GET /")
    r = requests.get(f"{BASE_URL}/")
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    print()

def test_stats():
    """Test stats endpoint"""
    print("Testing GET /stats/summary")
    r = requests.get(f"{BASE_URL}/stats/summary")
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    print()

def test_list_servers():
    """Test server list endpoint"""
    print("Testing GET /servers (premium, online, limit 10)")
    r = requests.get(f"{BASE_URL}/servers", params={
        "type": "PREMIUM",
        "status": "online",
        "page_size": 10
    })
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Total: {data['total']}")
    print(f"Page: {data['page']}/{data['total_pages']}")
    print(f"Servers returned: {len(data['servers'])}")
    if data['servers']:
        print(f"First server: {data['servers'][0]['ip']}")
    print()

def test_server_detail():
    """Test server detail endpoint"""
    print("Testing GET /servers/mc.hypixel.net")
    r = requests.get(f"{BASE_URL}/servers/mc.hypixel.net")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(json.dumps(r.json(), indent=2))
    else:
        print(r.text)
    print()

def test_health():
    """Test health endpoint"""
    print("Testing GET /health")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Enterprise API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_root()
        test_stats()
        test_list_servers()
        test_server_detail()
        
        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure it's running:")
        print("   python run_api.py")
    except Exception as e:
        print(f"❌ Test failed: {e}")
