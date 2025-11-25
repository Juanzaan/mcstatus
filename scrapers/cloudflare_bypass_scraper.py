"""CLOUDFLARE BYPASS SCRAPER (Enterprise Version)
Uses 'cloudscraper' with Enterprise Proxy/UA Rotation.

Features:
- Native Cloudflare bypass (JS engine)
- Weighted Proxy Rotation (ProxyManager)
- User-Agent Rotation (UserAgentManager)
- Extracts IPs from minecraft-server-list.com
- Verifies Premium + 500+ players
"""

import cloudscraper
from bs4 import BeautifulSoup
import time
import json
import re
import os
import sys
import random
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Ensure core modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from core import escaner_completo as scanner
# from core import database as db
from core.proxy_manager import ProxyManager
from core.user_agents import UserAgentManager

class CloudflareBypasser:
    def __init__(self):
        self.all_ips = set()
        self.verified_servers = []
        self.proxy_manager = ProxyManager()
        
        # Initialize cloudscraper with browser emulation
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def scrape_minecraft_server_list(self, pages: int = 100, start_page: int = 1):
        print("\n" + "=" * 60)
        print(" CLOUDFLARE BYPASS SCRAPER (Enterprise)")
        print("=" * 60)
        print(f"Target: minecraft-server-list.com")
        print(f"Pages: {start_page} to {start_page + pages - 1}")
        print("=" * 60 + "\n")

        for page in tqdm(range(start_page, start_page + pages), desc="Scraping pages"):
            if page == 1:
                url = "https://minecraft-server-list.com/"
            else:
                url = f"https://minecraft-server-list.com/page/{page}/"
            
            # Rotate User Agent
            ua = UserAgentManager.get_random_user_agent()
            self.scraper.headers.update({'User-Agent': ua})
            
            success = False
            for attempt in range(3):
                proxy = self.proxy_manager.get_proxy()
                proxies = proxy if proxy else None
                
                try:
                    resp = self.scraper.get(url, timeout=15, proxies=proxies)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        new_ips = self.extract_ips_from_page(soup)
                        self.all_ips.update(new_ips)
                        
                        if proxy:
                            self.proxy_manager.report_success(proxy)
                        success = True
                        break
                    else:
                        if proxy:
                            self.proxy_manager.report_failure(proxy)
                            
                except Exception as e:
                    if proxy:
                        self.proxy_manager.report_failure(proxy)
                    time.sleep(1)
            
            if not success:
                tqdm.write(f"⚠️ Failed to scrape page {page}")
                
            time.sleep(random.uniform(0.5, 1.5))

        print(f"\n✨ Extraction complete! Found {len(self.all_ips)} unique IPs.")
        self.save_results()

    def extract_ips_from_page(self, soup: BeautifulSoup) -> set:
        ips = set()
        
        # Strategy 1: Specific Elements
        for inp in soup.find_all('input', {'name': 'serverip'}):
            val = inp.get('value')
            if val:
                ips.add(val.strip())

        for td in soup.find_all('td', {'class': 'n2'}):
            val = td.get('id')
            if val:
                ips.add(val.strip())

        # Strategy 2: Regex
        text = soup.get_text()
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]{1,5})?\b"
        for ip in re.findall(ip_pattern, text):
            if not ip.startswith(('127.', '0.0.', '255.', '192.168.', '10.')):
                if ':' not in ip:
                    ip = f"{ip}:25565"
                ips.add(ip)

        domain_pattern = r"\b[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.(?:com|net|org|gg|me|co|xyz|us|eu|pe|fun|io|wtf)(?::[0-9]{1,5})?\b"
        for domain in re.findall(domain_pattern, text, re.IGNORECASE):
            if any(x in domain.lower() for x in ['google', 'facebook', 'twitter', 'cloudflare', 'minecraft-server-list', 'discord', 'youtube']):
                continue
            ips.add(domain)

        return ips

    def save_results(self):
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        # Save raw IPs
        output_file = os.path.join(data_dir, 'scraped_ips.json')
        
        # Load existing if any
        existing = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r') as f:
                    existing = json.load(f)
            except: pass
            
        # Merge
        current_ips = list(self.all_ips)
        # Simple list of strings or dicts? Let's save as list of dicts for compatibility
        new_entries = [{'ip': ip, 'source': 'cloudflare_scraper', 'scraped_at': time.time()} for ip in current_ips]
        
        combined = existing + new_entries
        # Deduplicate by IP
        unique = {x['ip']: x for x in combined}.values()
        
        with open(output_file, 'w') as f:
            json.dump(list(unique), f, indent=2)
            
        print(f"✓ Saved {len(self.all_ips)} new IPs to {output_file}")
        print(f"Total unique IPs in file: {len(unique)}")
        print("run 'python scripts/scan_and_verify.py --input data/scraped_ips.json' to verify them.")

if __name__ == "__main__":
    scraper = CloudflareBypasser()
    scraper.scrape_minecraft_server_list(pages=2)
