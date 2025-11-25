import json
import os
import re
import sqlite3
import urllib.request
from typing import Set, List, Tuple
from bs4 import BeautifulSoup
import time

# ----------------------------------------------------------------------
# Configuration – sources for public Minecraft server IPs
# ----------------------------------------------------------------------
SOURCES = {
    # minecraft-server-list.com - filter for 1.21+ Java/Bedrock servers
    "minecraft_server_list": {
        "enabled": True,
        "url_template": "https://minecraft-server-list.com/sort/Version/page/{page}/",
        "pages": 20,  # Scan first 20 pages
        "min_version": "1.21"
    },
    # MCSrvStat API endpoints
    "mcsrvstat": {
        "enabled": True,
        "urls": [
            "https://api.mcsrvstat.us/2/servers",
            "https://api.mcsrvstat.us/2/list/popular"
        ]
    }
}

IP_REGEX = re.compile(r"(?:(?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9][\w\.-]+\.[a-zA-Z]{2,})(?::\d{1,5})?")

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IPS_TXT = os.path.join(BASE_DIR, "ips.txt")
DB_PATH = os.path.join(BASE_DIR, "mcstatus.db")


def parse_version(version_str):
    """Parse version string to comparable format (e.g., '1.21' -> (1, 21))"""
    try:
        # Handle versions like "1.21", "1.21.1", "1.20.4"
        match = re.search(r'(\d+)\.(\d+)', version_str)
        if match:
            return (int(match.group(1)), int(match.group(2)))
    except:
        pass
    return (0, 0)


def scrape_minecraft_server_list(min_version="1.21", pages=20):
    """Scrape minecraft-server-list.com for Java/Bedrock servers with version >= min_version"""
    min_ver = parse_version(min_version)
    found_ips = set()
    
    print(f"[minecraft-server-list.com] Scraping for {min_version}+ servers...")
    
    for page in range(1, pages + 1):
        url = f"https://minecraft-server-list.com/sort/Version/page/{page}/"
        
        try:
            # Add delay to avoid rate limiting
            if page > 1:
                time.sleep(1)
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find server entries (adjust selector based on actual page structure)
            server_cards = soup.find_all('div', class_='server')
            if not server_cards:
                # Alternative: try finding table rows or other structures
                server_cards = soup.find_all('tr', class_='server-row')
            
            for card in server_cards:
                # Extract IP/hostname
                ip_elem = card.find('span', class_='ip') or card.find('a', class_='connect')
                if ip_elem:
                    ip = ip_elem.get_text(strip=True)
                    
                    # Extract version
                    version_elem = card.find('span', class_='version')
                    if version_elem:
                        version = version_elem.get_text(strip=True)
                        ver_tuple = parse_version(version)
                        
                        # Check if version meets minimum requirement
                        if ver_tuple >= min_ver:
                            # Check if it's Java or Java+Bedrock
                            platform_elem = card.find('span', class_='platform') or card.find('span', class_='type')
                            if platform_elem:
                                platform = platform_elem.get_text(strip=True).lower()
                                if 'java' in platform or 'bedrock' in platform:
                                    if IP_REGEX.match(ip):
                                        found_ips.add(ip)
                            else:
                                # If no platform specified, assume Java
                                if IP_REGEX.match(ip):
                                    found_ips.add(ip)
            
            print(f"  Page {page}/{pages}: Found {len(found_ips)} total IPs so far")
            
        except Exception as e:
            print(f"  Page {page} error: {e}")
            continue
    
    print(f"[minecraft-server-list.com] Found {len(found_ips)} servers with {min_version}+")
    return found_ips


def fetch_from_url(url: str) -> Set[str]:
    """Download a URL and extract any IP[:port] strings."""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[fetch] {url} → error: {e}")
        return set()

    # Try JSON first
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "servers" in data:
            # Extract IPs from server objects
            ips = set()
            for s in data["servers"]:
                if isinstance(s, dict) and s.get('ip'):
                    port = f":{s['port']}" if s.get('port') else ''
                    full_ip = f"{s['ip']}{port}"
                    if IP_REGEX.match(full_ip):
                        ips.add(full_ip)
            return ips
        if isinstance(data, list):
            return {ip for ip in data if IP_REGEX.match(ip)}
    except json.JSONDecodeError:
        pass

    # Plain‑text fallback
    return {m.group(0) for m in IP_REGEX.finditer(raw)}


def gather_all_ips() -> Set[str]:
    """Collect IPs from every enabled source and deduplicate them."""
    all_ips: Set[str] = set()
    
    # Scrape minecraft-server-list.com
    if SOURCES["minecraft_server_list"]["enabled"]:
        config = SOURCES["minecraft_server_list"]
        mc_ips = scrape_minecraft_server_list(
            min_version=config["min_version"],
            pages=config["pages"]
        )
        all_ips.update(mc_ips)
    
    # Fetch from MCSrvStat APIs
    if SOURCES["mcsrvstat"]["enabled"]:
        for url in SOURCES["mcsrvstat"]["urls"]:
            all_ips.update(fetch_from_url(url))
    
    return all_ips


def write_ips_to_file(ips: Set[str]) -> None:
    """Append only new IPs to ips.txt (one per line)."""
    existing: Set[str] = set()
    if os.path.exists(IPS_TXT):
        with open(IPS_TXT, "r", encoding="utf-8") as f:
            existing = {line.strip() for line in f if line.strip()}
    new_ips = ips - existing
    if not new_ips:
        print("[fetch] No new IPs found.")
        return
    with open(IPS_TXT, "a", encoding="utf-8") as f:
        for ip in sorted(new_ips):
            f.write(ip + "\n")
    print(f"[fetch] Added {len(new_ips)} new IPs to {IPS_TXT}.")


def insert_ips_into_db(ips: Set[str]) -> None:
    """Insert raw IP strings into the SQLite *servers* table (duplicates ignored)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS servers (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               ip TEXT UNIQUE,
               country TEXT,
               isp TEXT,
               auth_mode TEXT,
               version TEXT,
               online INTEGER,
               max_players INTEGER,
               premium INTEGER,
               cracked INTEGER,
               new_players INTEGER,
               icon TEXT,
               last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           );"""
    )
    for ip in ips:
        cur.execute("INSERT OR IGNORE INTO servers (ip) VALUES (?)", (ip,))
    conn.commit()
    conn.close()
    print(f"[db] Inserted {len(ips)} IPs into SQLite (duplicates ignored).")


def get_sorted_servers(order_by: str = "online DESC", limit: int = 100) -> List[Tuple]:
    """Return a list of server rows sorted by any column."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        f"""SELECT ip, country, isp, auth_mode, version, online,
                       premium, cracked, new_players, icon
                  FROM servers
                 WHERE online IS NOT NULL
                 ORDER BY {order_by}
                 LIMIT ?;""",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    print("=" * 60)
    print(" PUBLIC IP FETCHER - Gathering Minecraft Server IPs")
    print("=" * 60)
    
    # 1️⃣ Pull public IP lists
    ips = gather_all_ips()
    print(f"\nTotal unique IPs found: {len(ips)}")

    # 2️⃣ Persist to the plain‑text file used by the scanner
    write_ips_to_file(ips)

    # 3️⃣ Also push them into SQLite for instant sorting / querying
    insert_ips_into_db(ips)

    # 4️⃣ Example: show the top 10 servers by current online count
    top = get_sorted_servers(order_by="online DESC", limit=10)
    print("\nTop 10 servers by online count (from previous scans):")
    for r in top:
        print(f"  {r[0]} - {r[5]} players")
    
    print("\n✓ IP list updated successfully!")
