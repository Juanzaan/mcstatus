#!/usr/bin/env python3
"""Quick test to verify cloudscraper is working and IPs are being extracted"""
import cloudscraper
from bs4 import BeautifulSoup
import re

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

print("Fetching page 1...")
resp = scraper.get("https://minecraft-server-list.com/servers/1/", timeout=15)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, "html.parser")
    ips = set()
    
    # Extract from input elements
    for inp in soup.find_all('input', {'name': 'serverip'}):
        val = inp.get('value')
        if val:
            ips.add(val.strip())
            
    print(f"\n✓ Found {len(ips)} IPs from page 1:")
    for ip in sorted(list(ips)[:10]):  # Show first 10
        print(f"  - {ip}")
        
    if len(ips) > 10:
        print(f"  ... and {len(ips) - 10} more")
else:
    print("❌ Failed to fetch page")
