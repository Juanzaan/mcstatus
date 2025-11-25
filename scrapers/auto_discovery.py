"""
INTELLIGENT SERVER DISCOVERY SYSTEM
Automatically finds popular premium servers using multiple strategies

Strategies:
1. Network-based discovery (scan popular hosting providers)
2. DNS pattern matching (common server naming conventions)
3. API-based discovery (server network APIs)
4. Database mining (find patterns in existing successful scans)
5. Social media scraping (YouTube, Reddit server mentions)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core'))

from core import escaner_completo as scanner
from core import database as db


class IntelligentServerDiscovery:
    def __init__(self):
        self.discovered_ips = set()
        self.verified_servers = []
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        
    def scan_minehut_network(self):
        """Minehut hosts thousands of servers - scan their network"""
        print(f"\n{'='*60}")
        print(" STRATEGY 1: Minehut Network API")
        print(f"{'='*60}")
        
        try:
            # Minehut API endpoint for popular servers
            url = "https://api.minehut.com/servers"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                servers = data.get('servers', [])
                
                for server in servers:
                    player_count = server.get('playerCount', 0)
                    if player_count >= 500:  # Only high-pop servers
                        name = server.get('name', '')
                        # Minehut format: servername.minehut.gg
                        ip = f"{name}.minehut.gg:25565"
                        self.discovered_ips.add(ip)
                        
                print(f"✓ Found {len(self.discovered_ips)} Minehut servers with 500+ players")
        except Exception as e:
            print(f"✗ Minehut API error: {e}")
            
    def scan_common_network_patterns(self):
        """Scan common server naming patterns"""
        print(f"\n{'='*60}")
        print(" STRATEGY 2: Common Network Patterns")
        print(f"{'='*60}")
        
        # Popular hosting networks and their patterns
        patterns = [
            # Hypixel network
            "hypixel.net",
            "mc.hypixel.net",
            
            # Mineplex variants
            "mineplex.com",
            "us.mineplex.com",
            "eu.mineplex.com",
            "pe.mineplex.com",
            
            # CubeCraft
            "mc.cubecraft.net",
            "play.cubecraft.net",
            
            # The Hive
            "play.hivemc.com",
            "hivemc.com",
            
            # Wynncraft
            "play.wynncraft.com",
            
            # Complex Gaming
            "mc-complex.com",
            "play.mc-complex.com",
            "mp.mc-complex.com",
            
            # MCCentral
            "go.mccentral.org",
            "play.mccentral.org",
            
            # PvP Land
            "pvp.land",
            "play.pvp.land",
            
            # JartexNetwork
            "jartexnetwork.com",
            "play.jartexnetwork.com",
            
            # PikaNetwork
            "pika-network.net",
            "play.pika-network.net",
            
            # Invaded Lands
            "play.invadedlands.net",
            
            # Purple Prison
            "play.purpleprison.net",
            "play.purpleprison.xyz",
            
            # Mineverse
            "mineverse.com",
            "play.mineverse.com",
        ]
        
        for pattern in patterns:
            ip = f"{pattern}:25565" if ':' not in pattern else pattern
            self.discovered_ips.add(ip)
            
        print(f"✓ Added {len(patterns)} known large server patterns")
        
    def scan_database_for_popular(self):
        """Mine existing database for servers that USED to be popular"""
        print(f"\n{'='*60}")
        print(" STRATEGY 3: Database Mining")
        print(f"{'='*60}")
        
        try:
            # Get all servers from database that ever had 500+ players
            servers = db.get_latest_scan_data()
            
            for server in servers:
                if server.get('online', 0) >= 500 or server.get('max', 0) >= 1000:
                    self.discovered_ips.add(server['ip'])
                    
            print(f"✓ Found servers from database with high capacity/population")
        except Exception as e:
            print(f"✗ Database mining error: {e}")
            
    def scan_reddit_mentions(self):
        """Scrape r/mcservers for popular server mentions"""
        print(f"\n{'='*60}")
        print(" STRATEGY 4: Reddit Server Mentions")
        print(f"{'='*60}")
        
        try:
            # Top posts from r/mcservers
            url = "https://www.reddit.com/r/mcservers/top/.json?limit=100"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) mcstatus/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]{1,5})?\b'
                domain_pattern = r'\b[a-zA-Z0-9][\w\.-]+\.(com|net|org|gg|me|co|xyz)(?::[0-9]{1,5})?\b'
                
                for post in posts:
                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')
                    
                    # Look for IPs in title and text
                    text = f"{title} {selftext}"
                    
                    ips = re.findall(ip_pattern, text)
                    domains = re.findall(domain_pattern, text)
                    
                    for ip in ips + [d[0] for d in domains]:
                        if ':' not in ip:
                            ip = f"{ip}:25565"
                        self.discovered_ips.add(ip)
                        
                print(f"✓ Found server mentions from Reddit")
                
            time.sleep(2)  # Reddit rate limit
            
        except Exception as e:
            print(f"✗ Reddit scraping error: {e}")
            
    def scan_server_network_apis(self):
        """Query various server network APIs"""
        print(f"\n{'='*60}")
        print(" STRATEGY 5: Server Network APIs")
        print(f"{'='*60}")
        
        # Aternos popular servers
        try:
            url = "https://aternos.org/servers/"
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract server addresses
            server_links = soup.find_all('a', href=True)
            for link in server_links:
                href = link.get('href', '')
                if 'aternos' in href:
                    # Extract server subdomain
                    match = re.search(r'([a-zA-Z0-9-]+)\.aternos', href)
                    if match:
                        server_name = match.group(0)
                        self.discovered_ips.add(f"{server_name}:25565")
                        
            print(f"✓ Scanned Aternos network")
        except Exception as e:
            print(f"✗ Aternos API error: {e}")
            
    def verify_and_filter_premium_500plus(self):
        """Verify all discovered servers for Premium + 500+ players"""
        print(f"\n{'='*60}")
        print(f" VERIFICATION PHASE")
        print(f"{'='*60}")
        print(f"Total discovered IPs: {len(self.discovered_ips):,}")
        print("Filter: PREMIUM authentication + 500+ players")
        print(f"{'='*60}\n")
        
        db.init_db()
        scan_id = db.create_scan()
        player_db = db.get_all_player_uuids()
        settings = scanner.load_settings()
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = {
                executor.submit(scanner.analizar_servidor_completo, ip, player_db, settings): ip 
                for ip in self.discovered_ips
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Verifying", unit="server"):
                try:
                    (datos, nuevos) = future.result(timeout=10)
                    
                    if datos:
                        # Check criteria
                        is_premium = datos.get('auth_mode') == 'PREMIUM'
                        has_500plus = datos.get('online', 0) >= 500
                        
                        if is_premium and has_500plus:
                            db.save_server_data(scan_id, datos)
                            self.verified_servers.append(datos)
                            
                            # Print immediately when found
                            tqdm.write(f"✓ Found: {datos['ip']} - {datos.get('online', 0)} players")
                            
                except Exception:
                    continue
        
        print(f"\n✓ Verified {len(self.verified_servers)} Premium 500+ servers!")
        
    def save_results(self):
        """Save discovered servers"""
        print(f"\n{'='*60}")
        print(" SAVING RESULTS")
        print(f"{'='*60}")
        
        # Save all discovered IPs
        with open('../data/discovered_ips.txt', 'w') as f:
            for ip in sorted(self.discovered_ips):
                f.write(ip + '\n')
        print(f"✓ Saved {len(self.discovered_ips)} discovered IPs")
        
        # Save verified servers
        with open('../data/auto_discovered_premium_500plus.json', 'w') as f:
            json.dump(self.verified_servers, f, indent=2)
        print(f"✓ Saved {len(self.verified_servers)} verified servers")
        
        # Merge with existing large_premium_servers.json
        try:
            with open('../data/large_premium_servers.json', 'r') as f:
                existing = json.load(f)
                
            # Combine and deduplicate
            all_servers = {s['ip']: s for s in existing + self.verified_servers}
            merged = list(all_servers.values())
            
            with open('../data/large_premium_servers.json', 'w') as f:
                json.dump(merged, f, indent=2)
                
            print(f"✓ Merged with existing data: {len(merged)} total unique servers")
        except:
            pass
            
        # Print summary
        self.print_summary()
        
    def print_summary(self):
        """Print final summary"""
        print(f"\n{'='*60}")
        print(" DISCOVERY SUMMARY")
        print(f"{'='*60}")
        print(f"Total IPs discovered: {len(self.discovered_ips):,}")
        print(f"Premium 500+ verified: {len(self.verified_servers)}")
        
        if self.verified_servers:
            total_players = sum(s.get('online', 0) for s in self.verified_servers)
            print(f"Total combined players: {total_players:,}")
            
            sorted_servers = sorted(
                self.verified_servers, 
                key=lambda x: x.get('online', 0), 
                reverse=True
            )
            
            print(f"\n🏆 TOP 10 NEWLY DISCOVERED SERVERS:")
            print("-" * 60)
            for i, s in enumerate(sorted_servers[:10], 1):
                print(f"{i:2}. {s['ip']:35} {s.get('online', 0):>6} players")
        
        print(f"\n{'='*60}")
        print("✅ AUTO-DISCOVERY COMPLETE!")
        print(f"{'='*60}\n")


def main():
    print(f"\n{'='*70}")
    print(f" 🤖 INTELLIGENT SERVER AUTO-DISCOVERY")
    print(f"{'='*70}")
    print(" Using 5 smart strategies to find popular premium servers")
    print(f"{'='*70}\n")
    
    discovery = IntelligentServerDiscovery()
    
    # Run all discovery strategies
    discovery.scan_common_network_patterns()
    discovery.scan_minehut_network()
    discovery.scan_database_for_popular()
    discovery.scan_reddit_mentions()
    discovery.scan_server_network_apis()
    
    print(f"\n{'='*60}")
    print(f" DISCOVERY COMPLETE: {len(discovery.discovered_ips)} unique IPs")
    print(f"{'='*60}")
    
    # Verify all discovered servers
    if discovery.discovered_ips:
        discovery.verify_and_filter_premium_500plus()
        discovery.save_results()
    else:
        print("\n⚠️ No servers discovered!")


if __name__ == "__main__":
    main()
