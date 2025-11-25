"""Universal Server Scanner - Verifies any list of Minecraft server IPs
Can read from: TXT files, JSON files, or direct IP lists
Outputs verified server data in unified format
"""
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.escaner_completo import analizar_servidor_completo, load_settings
from core.database import init_db, create_scan, get_all_player_uuids, save_server_data

class UniversalScanner:
    def __init__(self, max_workers: int = 50):
        self.max_workers = max_workers
        self.data_dir = Path(__file__).parent.parent / "data"
        self.verified_servers = []
        
    def load_ips_from_txt(self, filepath: str) -> List[str]:
        """Load IPs from text file (one per line)"""
        ips = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                ip = line.strip()
                if ip and not ip.startswith('#'):
                    ips.append(ip)
        return ips
    
    def load_ips_from_json(self, filepath: str) -> List[str]:
        """Load IPs from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        ips = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    ips.append(item)
                elif isinstance(item, dict):
                    ips.append(item.get('ip', item.get('address', '')))
        elif isinstance(data, dict):
            servers = data.get('servers', data.get('premium', data.get('non_premium', [])))
            for server in servers:
                if isinstance(server, str):
                    ips.append(server)
                elif isinstance(server, dict):
                    ips.append(server.get('ip', server.get('address', '')))
        
        return [ip for ip in ips if ip]
    
    def load_ips_from_source(self, source: str) -> List[str]:
        """Auto-detect and load IPs from any source"""
        source_path = Path(source)
        
        if not source_path.exists():
            # Try in data directory
            source_path = self.data_dir / source
            
        if not source_path.exists():
            print(f"❌ Source not found: {source}")
            return []
        
        print(f"📂 Loading IPs from: {source_path.name}")
        
        if source_path.suffix == '.txt':
            return self.load_ips_from_txt(str(source_path))
        elif source_path.suffix == '.json':
            return self.load_ips_from_json(str(source_path))
        else:
            print(f"⚠️ Unknown file type: {source_path.suffix}")
            return []
    
    def scan_server(self, ip: str, player_db: Set[str], settings: Dict) -> Dict[str, Any]:
        """Scan a single server"""
        try:
            datos, _ = analizar_servidor_completo(ip, player_db, settings)
            return datos
        except Exception as e:
            return None
    
    def scan_all(self, ips: List[str], filter_premium: bool = False, 
                 min_players: int = 0, save_to: str = None):
        """Scan all IPs with multithreading"""
        print(f"\n🔍 Scanning {len(ips)} servers...")
        print(f"   Workers: {self.max_workers}")
        if filter_premium:
            print(f"   Filter: Premium servers with {min_players}+ players")
        print("=" * 60)
        
        # Initialize
        init_db()
        scan_id = create_scan()
        player_db = get_all_player_uuids()
        settings = load_settings()
        
        results = {
            'online': [],
            'offline': [],
            'premium': [],
            'non_premium': []
        }
        
        # Scan with progress bar
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.scan_server, ip, player_db, settings): ip 
                for ip in ips
            }
            
            for future in tqdm(as_completed(futures), total=len(futures), 
                             desc="Scanning", unit="server"):
                ip = futures[future]
                try:
                    data = future.result(timeout=15)
                    
                    if data and data.get('online', 0) > 0:
                        # Server is online
                        results['online'].append(data)
                        
                        # Categorize
                        auth_mode = data.get('auth_mode', 'UNKNOWN')
                        online = data.get('online', 0)
                        
                        if auth_mode == 'PREMIUM' and online >= min_players:
                            results['premium'].append(data)
                            save_server_data(scan_id, data)
                            tqdm.write(f"✓ {ip} - {online} players (Premium)")
                        else:
                            results['non_premium'].append(data)
                            if not filter_premium:
                                save_server_data(scan_id, data)
                    else:
                        # Offline or failed
                        results['offline'].append({'ip': ip, 'status': 'offline'})
                        
                except Exception as e:
                    results['offline'].append({'ip': ip, 'status': 'error'})
        
        # Summary
        print(f"\n📊 Scan Results:")
        print(f"   Online: {len(results['online'])}")
        print(f"   Premium: {len(results['premium'])}")
        print(f"   Non-Premium: {len(results['non_premium'])}")
        print(f"   Offline: {len(results['offline'])}")
        
        # Save results
        if save_to:
            output_file = self.data_dir / save_to
            save_data = {
                'premium': results['premium'],
                'non_premium': results['non_premium'],
                'stats': {
                    'total_scanned': len(ips),
                    'total_online': len(results['online']),
                    'total_premium': len(results['premium']),
                    'total_non_premium': len(results['non_premium']),
                    'total_offline': len(results['offline'])
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Saved results to: {output_file}")
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Minecraft Server Scanner')
    parser.add_argument('source', help='Source file (txt or json) with IPs to scan')
    parser.add_argument('--output', '-o', help='Output JSON file', 
                       default='scan_results.json')
    parser.add_argument('--workers', '-w', type=int, default=50,
                       help='Number of concurrent workers (default: 50)')
    parser.add_argument('--premium-only', action='store_true',
                       help='Only save premium servers')
    parser.add_argument('--min-players', type=int, default=500,
                       help='Minimum players for premium filter (default: 500)')
    
    args = parser.parse_args()
    
    # Create scanner
    scanner_obj = UniversalScanner(max_workers=args.workers)
    
    # Load IPs
    ips = scanner_obj.load_ips_from_source(args.source)
    if not ips:
        print("❌ No IPs found to scan")
        return
    
    print(f"✓ Loaded {len(ips)} unique IPs")
    
    # Scan
    results = scanner_obj.scan_all(
        ips, 
        filter_premium=args.premium_only,
        min_players=args.min_players,
        save_to=args.output
    )
    
    # Show top results
    if results['premium']:
        print(f"\n🏆 Top Premium Servers:")
        top = sorted(results['premium'], key=lambda x: x.get('online', 0), reverse=True)[:10]
        for i, srv in enumerate(top, 1):
            print(f"  {i:2}. {srv['ip']:30} {srv.get('online', 0):>6} players")

if __name__ == "__main__":
    main()
