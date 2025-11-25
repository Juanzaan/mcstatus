import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests
import time
import os

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "servers.db")

def normalize_server_address(address: str, remove_www: bool = True) -> str:
    """
    Enhanced normalization with punycode (IDN) and www removal support.
    
    Rules:
    - Lowercase hostname
    - Remove default port :25565
    - Strip whitespace
    - Remove protocol prefixes
    - Handle punycode/IDN (internationalized domain names)
    - Optionally remove www. prefix (configurable)
    
    Examples:
        'Play.Hypixel.NET:25565' -> 'play.hypixel.net'
        'www.Server.com' -> 'server.com' (if remove_www=True)
        'münchen.de' -> 'xn--mnchen-3ya.de' (punycode)
    """
    if not address:
        return address
    
    # Strip whitespace
    address = address.strip()
    
    # Remove protocol prefixes
    for prefix in ['minecraft://', 'mc://', 'http://', 'https://']:
        if address.lower().startswith(prefix):
            address = address[len(prefix):]
    
    # Handle punycode (IDN - Internationalized Domain Names)
    try:
        if ':' in address:
            host, port = address.rsplit(':', 1)
            # Encode to punycode and lowercase
            host = host.encode('idna').decode('ascii').lower()
            address = f"{host}:{port}"
        else:
            address = address.encode('idna').decode('ascii').lower()
    except (UnicodeError, UnicodeDecodeError, UnicodeEncodeError):
        # Fallback to simple lowercase if punycode fails
        if ':' in address:
            host, port = address.rsplit(':', 1)
            address = f"{host.lower()}:{port}"
        else:
            address = address.lower()
    
    # Remove 'www.' prefix (configurable)
    if remove_www and address.startswith('www.'):
        address = address[:4]
    
    # Remove default port :25565
    if address.endswith(':25565'):
        address = address[:-6]
    
    return address

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Scans table - tracks each scan run
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Servers table - unique server registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            ip TEXT PRIMARY KEY,
            country TEXT,
            isp TEXT,
            auth_mode TEXT,
            icon TEXT,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Server snapshots - point-in-time data for each scan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS server_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            ip TEXT,
            version TEXT,
            online INTEGER,
            max_players INTEGER,
            sample_size INTEGER,
            premium_count INTEGER,
            cracked_count INTEGER,
            new_players INTEGER,
            FOREIGN KEY (scan_id) REFERENCES scans(scan_id),
            FOREIGN KEY (ip) REFERENCES servers(ip)
        )
    """)
    
    # Players table - unique player tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            uuid TEXT PRIMARY KEY,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Geolocation cache - avoid repeated API calls
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geo_cache (
            ip TEXT PRIMARY KEY,
            country TEXT,
            isp TEXT,
            cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_scan ON server_snapshots(scan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ip ON server_snapshots(ip)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_lastseen ON servers(last_seen)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_cache_date ON geo_cache(cached_at)")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def create_scan():
    """Create a new scan entry and return its ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scans DEFAULT VALUES")
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id

def save_server_data(scan_id, server_data):
    """Save server data for a specific scan."""
    # Normalize IP before saving
    server_data['ip'] = normalize_server_address(server_data['ip'])
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Update or insert server
    cursor.execute("""
        INSERT INTO servers (ip, country, isp, auth_mode, icon, last_seen)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(ip) DO UPDATE SET
            country = excluded.country,
            isp = excluded.isp,
            auth_mode = excluded.auth_mode,
            icon = excluded.icon,
            last_seen = CURRENT_TIMESTAMP
    """, (server_data['ip'], server_data['country'], server_data['isp'], 
          server_data['auth_mode'], server_data.get('icon')))
    
    # Insert snapshot
    cursor.execute("""
        INSERT INTO server_snapshots 
        (scan_id, ip, version, online, max_players, sample_size, premium_count, cracked_count, new_players)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (scan_id, server_data['ip'], server_data['version'], server_data['online'],
          server_data['max'], server_data['sample_size'], server_data['premium'],
          server_data['cracked'], server_data['new_players']))
    
    conn.commit()
    conn.close()

def save_player(uuid):
    """Save or update a player's last seen time."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO players (uuid, last_seen)
        VALUES (?, CURRENT_TIMESTAMP)
        ON CONFLICT(uuid) DO UPDATE SET last_seen = CURRENT_TIMESTAMP
    """, (uuid,))
    conn.commit()
    conn.close()

def get_all_player_uuids():
    """Get all known player UUIDs as a set."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT uuid FROM players")
    uuids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return uuids

def get_cached_geolocation(ip, ttl_days=30):
    """Get cached geolocation if available and not expired.
    Returns (country, isp) tuple or None if cache miss."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cutoff = datetime.now() - timedelta(days=ttl_days)
    cursor.execute("""
        SELECT country, isp FROM geo_cache
        WHERE ip = ? AND cached_at > ?
    """, (ip, cutoff))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

def save_geolocation_cache(ip, country, isp):
    """Save geolocation data to cache."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO geo_cache (ip, country, isp, cached_at)
        VALUES (?, ?, ?,CURRENT_TIMESTAMP)
        ON CONFLICT(ip) DO UPDATE SET
            country = excluded.country,
            isp = excluded.isp,
            cached_at = CURRENT_TIMESTAMP
    """, (ip, country, isp))
    conn.commit()
    conn.close()

def get_latest_scan_data():
    """Get the most recent scan data for all servers."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # PHASE 11: Filter only canonical servers
    cursor.execute("""
        SELECT 
            s.ip, s.country, s.isp, s.auth_mode, s.icon, s.alternate_ips,
            s.is_canonical, s.canonical_id,
            ss.version, ss.online, ss.max_players, ss.sample_size,
            ss.premium_count, ss.cracked_count, ss.new_players
        FROM servers s
        JOIN server_snapshots ss ON s.ip = ss.ip
        WHERE s.is_canonical = 1 AND ss.id = (
            SELECT MAX(id) 
            FROM server_snapshots 
            WHERE ip = s.ip
        )
        AND (s.is_canonical IS NULL OR s.is_canonical = 1)
        ORDER BY ss.online DESC
    """)
    
    rows = cursor.fetchall()
    print(f"DEBUG: get_latest_scan_data found {len(rows)} servers")
    
    servers = []
    for row in rows:
        # Parse alternate_ips if present
        alternate_ips = []
        if row['alternate_ips']:
            alternate_ips = [ip.strip() for ip in row['alternate_ips'].split(',')]
        
        servers.append({
            'ip': row['ip'],
            'name': row['ip'],  # Use IP as name for now
            'description': '',  # Empty description for now
            'country': row['country'],
            'isp': row['isp'],
            'auth_mode': row['auth_mode'],
            'version': row['version'],
            'online': row['online'],
            'max': row['max_players'],
            'sample_size': row['sample_size'],
            'premium': row['premium_count'],
            'cracked': row['cracked_count'],
            'new_players': row['new_players'],
            'icon': row['icon'],
            'alternate_ips': alternate_ips,
            'is_canonical': row['is_canonical'] if 'is_canonical' in row.keys() else True,
            'known_aliases': []  # Will be populated later if needed
        })
    
    conn.close()
    return servers

def get_servers_to_scan(limit=None, order_by='last_seen'):
    """Get servers to scan, prioritizing oldest scans."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT ip, auth_mode FROM servers"
    
    if order_by == 'last_seen':
        query += " ORDER BY last_seen ASC"
    elif order_by == 'random':
        query += " ORDER BY RANDOM()"
        
    if limit:
        query += f" LIMIT {limit}"
        
    cursor.execute(query)
    servers = [{'ip': row['ip'], 'auth_mode': row['auth_mode']} for row in cursor.fetchall()]
    conn.close()
    return servers

def save_batch_results(scan_id, results):
    """Save a batch of scan results to the database."""
    if not results:
        return
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Prepare data for bulk insert
        server_updates = []
        snapshot_inserts = []
        alternate_ips_updates = {}  # Track alternate IPs
        
        for res in results:
            ip = res.get('ip')
            if not ip: continue
            
            # Store original IP before normalization
            original_ip = ip
            
            # Normalize IP
            ip = normalize_server_address(ip)
            res['ip'] = ip
            
            # Track if this was a variant (different from normalized)
            if original_ip != ip:
                if ip not in alternate_ips_updates:
                    # Check existing alternates
                    cursor.execute("SELECT alternate_ips FROM servers WHERE ip = ?", (ip,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        existing = [a.strip() for a in row[0].split(',')]
                    else:
                        existing = []
                    alternate_ips_updates[ip] = existing
                
                # Add this variant if not already tracked
                if original_ip not in alternate_ips_updates[ip]:
                    alternate_ips_updates[ip].append(original_ip)
            
            # Update servers table
            server_updates.append((
                res.get('country', 'Unknown'),
                res.get('isp', 'Unknown'),
                res.get('auth_mode', 'UNKNOWN'),
                res.get('icon'),
                datetime.now().isoformat(),
                ip
            ))
            
            # Insert into server_snapshots
            snapshot_inserts.append((
                scan_id,
                ip,
                res.get('version', 'Unknown'),
                res.get('players_actual', 0), # online column stores player count
                res.get('players_max', 0),
                res.get('sample_size', 0),
                res.get('premium', 0), # premium_count
                res.get('cracked', 0), # cracked_count
                res.get('new_players', 0)
            ))
            
        # Bulk update servers
        cursor.executemany("""
            UPDATE servers 
            SET country=?, isp=?, auth_mode=?, icon=?, last_seen=?
            WHERE ip=?
        """, server_updates)
        
        # Bulk insert snapshots
        cursor.executemany("""
            INSERT INTO server_snapshots (
                scan_id, ip, version, online, max_players, 
                sample_size, premium_count, cracked_count, new_players
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, snapshot_inserts)
        
        # Delete offline servers immediately
        offline_ips = [ip for ip, _, _, online, *_ in snapshot_inserts if online == 0]
        if offline_ips:
            print(f"🗑️ Auto-deleting {len(offline_ips)} offline servers...")
            for ip in offline_ips:
                # Delete all snapshots for this server
                cursor.execute("DELETE FROM server_snapshots WHERE ip = ?", (ip,))
                # Delete server record
                cursor.execute("DELETE FROM servers WHERE ip = ?", (ip,))
        
        # Update alternate IPs
        for ip, alternates in alternate_ips_updates.items():
            alternates_str = ', '.join(alternates)
            cursor.execute("""
                UPDATE servers 
                SET alternate_ips = ?
                WHERE ip = ?
            """, (alternates_str, ip))
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ Error saving batch results: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

def get_server_trend(ip, hours=24):
    """Get player count trend for a server over the last N hours."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cutoff = datetime.now() - timedelta(hours=hours)
    cursor.execute("""
        SELECT ss.online, sc.timestamp
        FROM server_snapshots ss
        JOIN scans sc ON ss.scan_id = sc.scan_id
        WHERE ss.ip = ? AND sc.timestamp > ?
        ORDER BY sc.timestamp ASC
    """, (ip, cutoff))
    
    trend_data = [{'online': row[0], 'timestamp': row[1]} for row in cursor.fetchall()]
    conn.close()
    
    # Calculate change
    if len(trend_data) >= 2:
        first = trend_data[0]['online']
        last = trend_data[-1]['online']
        change = last - first
        return {'change': change, 'direction': 'up' if change > 0 else 'down' if change < 0 else 'stable', 'data': trend_data}
    
    return {'change': 0, 'direction': 'stable', 'data': trend_data}

def get_global_trend(hours=24):
    """Get global player count trend over the last N hours."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cutoff = datetime.now() - timedelta(hours=hours)
    cursor.execute("""
        SELECT SUM(ss.online) as total_players, sc.timestamp
        FROM server_snapshots ss
        JOIN scans sc ON ss.scan_id = sc.scan_id
        WHERE sc.timestamp > ?
        GROUP BY sc.scan_id
        ORDER BY sc.timestamp ASC
    """, (cutoff,))
    
    trend_data = [{'total_players': row[0], 'timestamp': row[1]} for row in cursor.fetchall()]
    conn.close()
    return trend_data

def get_stats():
    """Get global statistics."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get latest scan stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_servers,
            SUM(ss.online) as total_players,
            AVG(ss.online) as avg_players,
            SUM(CASE WHEN s.auth_mode = 'PREMIUM' THEN 1 ELSE 0 END) as premium_count,
            SUM(CASE WHEN s.auth_mode IN ('NO-PREMIUM', 'CRACKED') THEN 1 ELSE 0 END) as cracked_count
        FROM servers s
        JOIN server_snapshots ss ON s.ip = ss.ip
        WHERE s.is_canonical = 1 AND ss.id = (
            SELECT MAX(id) 
            FROM server_snapshots 
            WHERE ip = s.ip
        )
    """)
    
    row = cursor.fetchone()
    stats = {
        'total_servers': row[0] or 0,
        'total_players': row[1] or 0,
        'avg_players': round(row[2] or 0, 1),
        'premium_count': row[3] or 0,
        'cracked_count': row[4] or 0,
        'premium_percent': round((row[3] or 0) / (row[0] or 1) * 100, 1)
    }
    
    conn.close()
    return stats

def export_for_dashboard():
    """Export data in the format expected by dashboard.html"""
    servers = get_latest_scan_data()
    
    # Add trend data to each server
    for server in servers:
        trend = get_server_trend(server['ip'])
        server['trend'] = trend['direction']
        server['trend_change'] = trend['change']
    
    # Get global trend
    global_trend = get_global_trend()
    
    # Get stats
    stats = get_stats()
    
    return {
        'servers': servers,
        'global_trend': global_trend,
        'stats': stats
    }

# ========== PHASE 11: Alias Resolution Functions ==========

def resolve_alias_to_canonical(search_term: str) -> Optional[str]:
    """
    Check if search_term is an alias. If yes, return canonical IP.
    If no, return None (caller should search canonical servers directly).
    
    Args:
        search_term: IP or hostname to check
        
    Returns:
        Canonical IP if search_term is an alias, None otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT canonical_ip 
        FROM server_aliases 
        WHERE LOWER(alias_ip) = LOWER(?)
    """, (search_term,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None

def get_aliases_for_server(canonical_ip: str, prioritize: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Get all known aliases for a canonical server.
    
    Args:
        canonical_ip: The canonical server IP
        prioritize: Optional alias to move to top of list (contextual priority)
        limit: Maximum number of aliases to return (default 5)
        
    Returns:
        List of alias IPs (with prioritized alias first if specified)
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT alias_ip 
        FROM server_aliases 
        WHERE canonical_ip = ?
        ORDER BY confidence_score DESC, created_at DESC
    """, (canonical_ip,))
    
    aliases = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Enhancement 1: Contextual Alias Priority
    if prioritize and prioritize in aliases:
        # Move prioritized alias to front
        aliases.remove(prioritize)
        aliases.insert(0, prioritize)
    
    return aliases[:limit]

def get_server_by_ip(ip: str) -> Optional[Dict]:
    """
    Get a single server by IP (canonical only).
    
    Args:
        ip: Server IP to fetch
        
    Returns:
        Server dict or None if not found
    """
    servers = get_latest_scan_data()
    for server in servers:
        if server['ip'].lower() == ip.lower():
            return server
    return None

def ensure_alias_index():
    """
    Enhancement 2: Performance Safety - Ensure alias_ip is indexed.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_server_aliases_alias_ip 
            ON server_aliases(alias_ip)
        """)
        conn.commit()
        print("✅ Alias index verified/created")
    except Exception as e:
        print(f"⚠️  Index creation failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Initialize database if run directly
    init_db()
    print("Database ready!")
