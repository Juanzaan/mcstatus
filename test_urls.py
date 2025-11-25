#!/usr/bin/env python3
"""Test different URL structures"""
import cloudscraper

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)

urls_to_try = [
    "https://minecraft-server-list.com/",
    "https://minecraft-server-list.com/page/2/",
    "https://minecraft-server-list.com/servers/",
]

for url in urls_to_try:
    print(f"\nTrying: {url}")
    resp = scraper.get(url, timeout=15)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        # Quick check for server entries
        has_serverip = 'name="serverip"' in resp.text
        print(f"  Has serverip inputs: {has_serverip}")
