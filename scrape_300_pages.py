"""
Simple working scraper for minecraft-server-list.com
Scrapes 300 pages using cloudscraper (bypasses Cloudflare)
"""
import cloudscraper
from bs4 import BeautifulSoup
import time
import re
from tqdm import tqdm
from datetime import datetime
import os

def scrape_mc_server_list(pages=300):
    """Scrape minecraft-server-list.com"""
    print(f"\n{'='*70}")
    print(" MINECRAFT SERVER LIST SCRAPER")
    print(f"{'='*70}")
    print(f" Target: minecraft-server-list.com")
    print(f" Pages: {pages}")
    print(f"{'='*70}\n")
    
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    all_ips = set()
    
    for page in tqdm(range(1, pages + 1), desc="Scraping"):
        try:
            # URL format: page 1 is /, page 2+ is /page/N/
            url = f"https://minecraft-server-list.com/page/{page}/" if page > 1 else "https://minecraft-server-list.com/"
            
            resp = scraper.get(url, timeout=15)
            if resp.status_code != 200:
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract IPs from inputs
            for inp in soup.find_all('input', {'name': 'serverip'}):
                val = inp.get('value')
                if val:
                    all_ips.add(val.strip())
            
            # Extract from <td class="n2" id="...">
            for td in soup.find_all('td', {'class': 'n2'}):
                val = td.get('id')
                if val:
                    all_ips.add(val.strip())
            
            # Regex for IPs and domains in text
            text = soup.get_text()
            for ip in re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]{1,5})?\b', text):
                if not ip.startswith(('127.', '0.0.', '255.', '192.168.', '10.')):
                    all_ips.add(ip if ':' in ip else f"{ip}:25565")
            
            for domain in re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.(?:com|net|org|gg|me|co|xyz|us|eu|pe|fun|io|wtf)(?::[0-9]{1,5})?\b', text, re.IGNORECASE):
                if not any(x in domain.lower() for x in ['google', 'facebook', 'twitter', 'cloudflare', 'minecraft-server-list', 'discord', 'youtube']):
                    all_ips.add(domain)
            
            if page % 10 == 0:
                tqdm.write(f"  {len(all_ips)} unique IPs collected")
            
            time.sleep(0.5)  # Polite delay
            
        except Exception as e:
            tqdm.write(f"Error page {page}: {str(e)[:50]}")
    
    return all_ips

if __name__ == "__main__":
    ips = scrape_mc_server_list(pages=300)
    
    print(f"\n✓ Total IPs found: {len(ips):,}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"data/minecraft_server_list_300pages_{timestamp}.txt"
    os.makedirs("data", exist_ok=True)
    
    with open(filepath, 'w') as f:
        for ip in sorted(ips):
            f.write(ip + '\n')
    
    print(f"✓ Saved to {filepath}")
    print(f"\n{'='*70}")
    print("✅ COMPLETE!")
    print(f"{'='*70}\n")
