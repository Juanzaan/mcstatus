"""Server List Merger - Unifies all server data sources into categorized lists"""
import json
import os
import re
from typing import Dict, List, Any
from pathlib import Path

class ServerMerger:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
            
        self.unified_data = {
            "premium": [],
            "non_premium": [],
            "offline": [],
            "stats": {
                "total_premium": 0,
                "total_non_premium": 0,
                "total_offline": 0,
                "total_players": 0
            }
        }
        
    def load_json_file(self, filename: str) -> List[Dict[str, Any]]:
        """Load JSON file, return empty list if not found"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list and dict formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and 'servers' in data:
                    return data['servers']
                return []
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []
    
    def categorize_server(self, server: Dict[str, Any]) -> str:
        """Categorize server as premium, non_premium, or offline"""
        online = server.get('online', 0)
        auth_mode = server.get('auth_mode', 'UNKNOWN')
        
        # Offline check
        if online == 0 or server.get('status') == 'offline':
            return 'offline'
        
        # Premium: any server with PREMIUM authentication
        if auth_mode == 'PREMIUM':
            return 'premium'
        
        # Everything else is non-premium
        return 'non_premium'
    
    def normalize_server(self, server: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize server data to consistent format"""
        return {
            'ip': server.get('ip', server.get('address', 'unknown')),
            'name': server.get('name', server.get('ip', 'Unknown Server')),
            'online': server.get('online', 0),
            'max_players': server.get('max_players', server.get('max', 0)),
            'auth_mode': server.get('auth_mode', 'UNKNOWN'),
            'version': server.get('version', 'Unknown'),
            'description': server.get('description', ''),
            'status': 'online' if server.get('online', 0) > 0 else 'offline',
            'last_seen': server.get('last_seen', server.get('timestamp', 'unknown'))
        }
    
    def normalize_ip_for_dedup(self, ip: str) -> str:
        """Normalize IP for deduplication (remove port for grouping)"""
        # Extract domain/IP without port
        if ':' in ip:
            return ip.split(':')[0]
        return ip
    
    def get_base_domain(self, ip: str) -> str:
        """Extract base domain name (SLD + TLD)"""
        # Remove port
        domain = self.normalize_ip_for_dedup(ip)
        
        # Skip if it's a raw IP address (xxx.xxx.xxx.xxx)
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
            return domain  # Keep raw IPs as-is
        
        parts = domain.split('.')
        if len(parts) >= 2:
            # Handle compound TLDs like co.uk, com.br
            if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in ['co', 'com', 'net', 'org', 'edu', 'gov', 'mil']:
                return '.'.join(parts[-3:]).lower()
            # Standard case: take last 2 parts (e.g. hypixel.net, minehut.gg)
            return '.'.join(parts[-2:]).lower()
        
        return domain.lower()

    def deduplicate_list(self, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate a list of servers using IP, Domain, and Name strategies"""
        
        # --- Pass 1: Deduplicate by IP (merge port variants) ---
        ip_groups = {}
        for server in servers:
            normalized_ip = self.normalize_ip_for_dedup(server['ip'])
            if normalized_ip not in ip_groups:
                ip_groups[normalized_ip] = []
            ip_groups[normalized_ip].append(server)
            
        unique_by_ip = []
        for group in ip_groups.values():
            if len(group) == 1:
                unique_by_ip.append(group[0])
            else:
                # Choose primary: highest online count
                primary = max(group, key=lambda s: s.get('online', 0))
                # Merge alternate IPs
                alternate_ips = set(primary.get('alternate_ips', []))
                for srv in group:
                    if srv['ip'] != primary['ip']:
                        alternate_ips.add(srv['ip'])
                    for alt in srv.get('alternate_ips', []):
                        if alt != primary['ip']:
                            alternate_ips.add(alt)
                primary['alternate_ips'] = list(alternate_ips)
                unique_by_ip.append(primary)
                
        # --- Pass 2: Deduplicate by Domain (merge TLD/Subdomain variants) ---
        domain_groups = {}
        for server in unique_by_ip:
            base_domain = self.get_base_domain(server['ip'])
            if base_domain not in domain_groups:
                domain_groups[base_domain] = []
            domain_groups[base_domain].append(server)
            
        unique_by_domain = []
        for group in domain_groups.values():
            if len(group) == 1:
                unique_by_domain.append(group[0])
            else:
                primary = max(group, key=lambda s: s.get('online', 0))
                alternate_ips = set(primary.get('alternate_ips', []))
                for srv in group:
                    if srv['ip'] != primary['ip']:
                        alternate_ips.add(srv['ip'])
                    for alt in srv.get('alternate_ips', []):
                        if alt != primary['ip']:
                            alternate_ips.add(alt)
                primary['alternate_ips'] = list(alternate_ips)
                unique_by_domain.append(primary)

        # --- Pass 3: Deduplicate by Name ---
        def normalize_name(name):
            name = name.lower().strip()
            for prefix in ['mc.', 'play.', 'hub.', 'lobby.', 'join.', 'go.', 'mp.', 'mcsl.', 'msl.', 'mcmp.']:
                if name.startswith(prefix):
                    name = name[len(prefix):]
            if ':' in name:
                name = name.split(':')[0]
            return name
            
        seen = {}
        final_unique = []
        
        for server in unique_by_domain:
            raw_name = server.get('name', server['ip']).lower().strip()
            normalized_name = normalize_name(raw_name)
            desc = server.get('description', '')[:100].lower().strip()
            fingerprint = f"{normalized_name}||{desc}"
            
            if (raw_name == server['ip'].lower() or 
                not raw_name or 
                raw_name == 'unknown server' or
                len(normalized_name) < 3):
                final_unique.append(server)
                continue
            
            if fingerprint not in seen:
                seen[fingerprint] = server
                final_unique.append(server)
            else:
                existing = seen[fingerprint]
                # Merge IPs
                current_ip = server['ip']
                existing_alts = set(existing.get('alternate_ips', []))
                if current_ip != existing['ip']:
                    existing_alts.add(current_ip)
                for alt in server.get('alternate_ips', []):
                    if alt != existing['ip']:
                        existing_alts.add(alt)
                existing['alternate_ips'] = list(existing_alts)
                
                if server.get('online', 0) > existing.get('online', 0):
                    idx = final_unique.index(existing)
                    server['alternate_ips'] = list(existing_alts)
                    final_unique[idx] = server
                    seen[fingerprint] = server
                    
        return final_unique
    
    def merge_all_sources(self):
        """Merge all server data sources"""
        print("🔄 Merging all server sources...")
        
        sources = [
            'large_premium_servers.json',
            'cloudflare_bypass_results.json',
            'auto_discovered_premium_500plus.json',
            'premium_500plus_verified.json',
            'verified_servers.json'
        ]
        
        seen_ips = set()
        all_servers = []
        
        # Load all servers first
        for source in sources:
            servers = self.load_json_file(source)
            print(f"  📂 {source}: {len(servers)} servers")
            
            for server in servers:
                normalized = self.normalize_server(server)
                ip = normalized['ip']
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    all_servers.append(normalized)
        
        # Load fallback IPs
        txt_file = self.data_dir / 'cloudflare_bypass_ips.txt'
        if txt_file.exists():
            with open(txt_file, 'r') as f:
                txt_ips = [line.strip() for line in f if line.strip()]
            print(f"  📂 cloudflare_bypass_ips.txt: {len(txt_ips)} IPs")
            for ip in txt_ips:
                if ip not in seen_ips:
                    seen_ips.add(ip)
                    all_servers.append({
                        'ip': ip,
                        'name': ip,
                        'online': 0,
                        'max_players': 0,
                        'auth_mode': 'UNKNOWN',
                        'version': 'Unknown',
                        'description': '',
                        'status': 'offline',
                        'last_seen': 'never'
                    })
        
        print(f"\n✓ Total raw servers: {len(all_servers)}")
        
        # Deduplicate GLOBALLY
        print("🔄 Running global deduplication...")
        unique_servers = self.deduplicate_list(all_servers)
        print(f"✓ Unique servers after deduplication: {len(unique_servers)}")
        
        # Categorize
        for server in unique_servers:
            category = self.categorize_server(server)
            self.unified_data[category].append(server)
            
            self.unified_data['stats'][f'total_{category}'] += 1
            if category in ['premium', 'non_premium']:
                self.unified_data['stats']['total_players'] += server['online']
        
        # Sort
        self.unified_data['premium'].sort(key=lambda x: x['online'], reverse=True)
        self.unified_data['non_premium'].sort(key=lambda x: x['online'], reverse=True)
        
        print(f"\n📊 Statistics:")
        print(f"  Premium: {self.unified_data['stats']['total_premium']}")
        print(f"  Non-Premium: {self.unified_data['stats']['total_non_premium']}")
        print(f"  Offline: {self.unified_data['stats']['total_offline']}")
        print(f"  Total Players: {self.unified_data['stats']['total_players']:,}")
    
    def save_unified_data(self):
        """Save unified data to file"""
        output_file = self.data_dir / 'unified_servers.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.unified_data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to {output_file}")
        return str(output_file)

def merge_all_servers():
    """Main function to merge all server lists"""
    merger = ServerMerger()
    merger.merge_all_sources()
    merger.save_unified_data()
    return merger.unified_data

if __name__ == "__main__":
    merge_all_servers()
