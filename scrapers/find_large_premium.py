"""
Premium Server Finder - Find servers with 500+ players and PREMIUM authentication

This script searches:
1. Local SQLite database
2. Public server lists (minecraft-mp.com, minecraftservers.org, etc.)
3. Top server ranking sites
"""

import sqlite3
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
import re
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DB_PATH = "../data/servers.db"

# Additional sources for large premium servers
LARGE_SERVER_SOURCES = [
    {
        "name": "minecraft-mp.com/popular",
        "url": "https://minecraft-mp.com/servers/",
        "pages": 10
    },
    {
        "name": "minecraftservers.org/popular",
        "url": "https://minecraftservers.org/",
        "pages": 5
    },
    {
        "name": "topminecraftservers.org",
        "url": "https://topminecraftservers.org/",
        "pages": 5
    }
]


def query_local_database():
    """Query local database for premium servers with 500+ players"""
    print("\n" + "="*60)
    print(" SEARCHING LOCAL DATABASE")
    print("="*60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get premium servers with 500+ players from latest scan
        cursor.execute("""
            SELECT 
                srv.ip,
                srv.country,
                srv.isp,
                srv.auth_mode,
                ss.version,
                ss.online,
                ss.max_players,
                srv.icon,
                srv.last_seen
            FROM servers srv
            JOIN server_snapshots ss ON srv.ip = ss.ip
            WHERE ss.scan_id = (SELECT MAX(scan_id) FROM scans)
                AND srv.auth_mode = 'PREMIUM'
                AND ss.online >= 500
            ORDER BY ss.online DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        servers = []
        for row in results:
            servers.append({
                'ip': row[0],
                'country': row[1],
                'isp': row[2],
                'auth_mode': row[3],
                'version': row[4],
                'online': row[5],
                'max': row[6],
                'icon': row[7],
                'last_seen': row[8],
                'source': 'Local DB'
            })
        
        print(f"✓ Found {len(servers)} premium servers with 500+ players")
        return servers
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        return []


def scrape_minecraft_mp(pages=10):
    """Scrape minecraft-mp.com for popular servers"""
    print("\n" + "="*60)
    print(" SCRAPING minecraft-mp.com (Popular Servers)")
    print("="*60)
    
    servers = []
    
    for page in range(1, pages + 1):
        url = f"https://minecraft-mp.com/servers/{page}/"
        
        try:
            time.sleep(1)  # Rate limiting
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find server entries
            server_rows = soup.find_all('div', class_='server')
            
            for row in server_rows:
                try:
                    # Extract IP
                    ip_elem = row.find('span', class_='ip')
                    if not ip_elem:
                        continue
                    ip = ip_elem.get_text(strip=True)
                    
                    # Extract player count
                    players_elem = row.find('span', class_='players')
                    if players_elem:
                        players_text = players_elem.get_text(strip=True)
                        # Parse "1234/2000" format
                        match = re.search(r'(\d+)', players_text)
                        if match:
                            online = int(match.group(1))
                            if online < 500:
                                continue
                        else:
                            continue
                    else:
                        continue
                    
                    # Extract country
                    country_elem = row.find('span', class_='country')
                    country = country_elem.get_text(strip=True) if country_elem else 'Unknown'
                    
                    servers.append({
                        'ip': ip,
                        'online': online,
                        'country': country,
                        'source': 'minecraft-mp.com',
                        'auth_mode': 'PENDING_VERIFICATION'  # Will scan later
                    })
                    
                except Exception as e:
                    continue
            
            print(f"  Page {page}/{pages}: Found {len(servers)} total candidates")
            
        except Exception as e:
            print(f"  Page {page} error: {e}")
            continue
    
    print(f"✓ Found {len(servers)} candidate servers from minecraft-mp.com")
    return servers


def scrape_minecraftservers_org(pages=5):
    """Scrape minecraftservers.org for popular servers"""
    print("\n" + "="*60)
    print(" SCRAPING minecraftservers.org")
    print("="*60)
    
    servers = []
    
    for page in range(1, pages + 1):
        url = f"https://minecraftservers.org/index/{page}"
        
        try:
            time.sleep(1)
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find server listings
            server_cards = soup.find_all('div', class_='server-item')
            
            for card in server_cards:
                try:
                    # Extract IP
                    ip_elem = card.find('span', class_='ip') or card.find('a', href=True)
                    if not ip_elem:
                        continue
                    ip = ip_elem.get_text(strip=True)
                    
                    # Extract players
                    players_elem = card.find('span', class_='online')
                    if players_elem:
                        players_text = players_elem.get_text(strip=True)
                        match = re.search(r'(\d+)', players_text)
                        if match:
                            online = int(match.group(1))
                            if online < 500:
                                continue
                        else:
                            continue
                    else:
                        continue
                    
                    servers.append({
                        'ip': ip,
                        'online': online,
                        'source': 'minecraftservers.org',
                        'auth_mode': 'PENDING_VERIFICATION'
                    })
                    
                except Exception:
                    continue
            
            print(f"  Page {page}/{pages}: Found {len(servers)} total candidates")
            
        except Exception as e:
            print(f"  Page {page} error: {e}")
            continue
    
    print(f"✓ Found {len(servers)} candidate servers from minecraftservers.org")
    return servers


def get_known_large_servers():
    """Return a list of known large premium servers"""
    known_servers = [
        "hypixel.net",
        "mineplex.com",
        "mc.cubecraft.net",
        "play.wynncraft.com",
        "mineverse.com",
        "minehut.com",
        "mc.herobrine.org",
        "pvp.land",
        "mc.vanitymc.co",
        "us.mineplex.com",
        "eu.mineplex.com",
        "pe.mineplex.com",
        "play.universemc.us",
        "play.hivemc.com",
        "mc.arkhamnetwork.org",
        "play.pixelmonrealms.com",
        "mc.performium.net",
        "mc.medievalrealms.net"
    ]
    
    print("\n" + "="*60)
    print(" KNOWN LARGE PREMIUM SERVERS")
    print("="*60)
    print(f"✓ Added {len(known_servers)} known large servers")
    
    return [{'ip': ip, 'source': 'Known Large Servers', 'auth_mode': 'PREMIUM'} 
            for ip in known_servers]


def save_to_file(servers, filename="large_premium_servers.json"):
    """Save results to JSON file"""
    # Sort by player count
    servers_sorted = sorted(servers, 
                           key=lambda x: x.get('online', 0), 
                           reverse=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(servers_sorted, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(servers_sorted)} servers to {filename}")


def save_ips_for_scanning(servers, filename="premium_500plus.txt"):
    """Save IPs to text file for scanning"""
    unique_ips = list(set([s['ip'] for s in servers]))
    
    with open(filename, 'w', encoding='utf-8') as f:
        for ip in unique_ips:
            f.write(ip + '\n')
    
    print(f"✓ Saved {len(unique_ips)} unique IPs to {filename}")


def display_summary(servers):
    """Display summary of found servers"""
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)
    
    # Count by source
    sources = {}
    auth_verified = {'PREMIUM': 0, 'PENDING_VERIFICATION': 0}
    
    for server in servers:
        source = server.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
        
        auth = server.get('auth_mode', 'PENDING_VERIFICATION')
        if auth == 'PREMIUM':
            auth_verified['PREMIUM'] += 1
        else:
            auth_verified['PENDING_VERIFICATION'] += 1
    
    print(f"\nTotal servers found: {len(servers)}")
    print(f"\nBy Source:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")
    
    print(f"\nAuthentication Status:")
    print(f"  Verified Premium: {auth_verified['PREMIUM']}")
    print(f"  Needs Verification: {auth_verified['PENDING_VERIFICATION']}")
    
    # Show top 10
    print(f"\n🏆 TOP 10 SERVERS BY PLAYER COUNT:")
    print("-" * 60)
    sorted_servers = sorted(servers, key=lambda x: x.get('online', 0), reverse=True)
    
    for i, server in enumerate(sorted_servers[:10], 1):
        online = server.get('online', '?')
        auth = server.get('auth_mode', '?')
        country = server.get('country', '?')
        print(f"{i:2}. {server['ip']:30} | {str(online):>6} players | {auth:15} | {country}")


def main():
    print("\n" + "="*60)
    print(" 🔍 PREMIUM SERVER FINDER (500+ Players)")
    print("="*60)
    print(" Searching multiple sources for large premium servers...")
    print("="*60)
    
    all_servers = []
    
    # 1. Search local database
    local_servers = query_local_database()
    all_servers.extend(local_servers)
    
    # 2. Add known large servers
    known_servers = get_known_large_servers()
    all_servers.extend(known_servers)
    
    # 3. Scrape minecraft-mp.com
    mp_servers = scrape_minecraft_mp(pages=10)
    all_servers.extend(mp_servers)
    
    # 4. Scrape minecraftservers.org
    # org_servers = scrape_minecraftservers_org(pages=5)
    # all_servers.extend(org_servers)
    
    # Remove duplicates
    unique_servers = {}
    for server in all_servers:
        ip = server['ip']
        if ip not in unique_servers or server.get('online', 0) > unique_servers[ip].get('online', 0):
            unique_servers[ip] = server
    
    final_servers = list(unique_servers.values())
    
    # Display results
    display_summary(final_servers)
    
    # Save results
    save_to_file(final_servers, "large_premium_servers.json")
    save_ips_for_scanning(final_servers, "premium_500plus.txt")
    
    print("\n" + "="*60)
    print(" ✅ COMPLETED")
    print("="*60)
    print("\nNext steps:")
    print("1. Review: large_premium_servers.json")
    print("2. Scan: python escaner_completo.py (will use premium_500plus.txt)")
    print("3. Verify premium status after scanning")
    print("\nNote: Servers marked 'PENDING_VERIFICATION' need to be scanned")
    print("      to confirm they are PREMIUM and have 500+ players.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
