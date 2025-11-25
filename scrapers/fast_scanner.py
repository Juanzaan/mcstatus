"""Fast Server Scanner - Two-phase optimized scanning
Phase 1: Quick scan (ping + basic status) - 200 workers, 3s timeout
Phase 2: Full scan only for online servers
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import socket
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcstatus import JavaServer
    from mcstatus.querier import QueryResponse
except ImportError:
    print("Installing mcstatus...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mcstatus>=12.0.0"])
    from mcstatus import JavaServer

class FastScanner:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        
    def quick_check(self, ip: str, timeout: int = 3) -> Dict:
        """Quick check: just ping and basic status"""
        try:
            # Add default port if missing
            if ':' not in ip:
                address = f"{ip}:25565"
            else:
                address = ip
            
            server = JavaServer.lookup(address, timeout=timeout)
            status = server.status()
            
            return {
                'ip': ip,
                'online': status.players.online,
                'max_players': status.players.max,
                'version': str(status.version.name),
                'description': str(status.description),
                'status': 'online'
            }
        except:
            return {'ip': ip, 'status': 'offline', 'online': 0}
    
    def full_scan(self, ip: str) -> Dict:
        """Full detailed scan - only for promising servers"""
        try:
            if ':' not in ip:
                address = f"{ip}:25565"
            else:
                address = ip
            
            server = JavaServer.lookup(address, timeout=5)
            status = server.status()
            
            # Try to determine auth mode
            auth_mode = "UNKNOWN"
            try:
                query = server.query()
                # Cracked servers usually have query enabled
                auth_mode = "CRACKED"
            except:
                # Premium servers often block query
                if status.players.online > 100:
                    auth_mode = "PREMIUM"
            
            return {
                'ip': ip,
                'name': ip,
                'online': status.players.online,
                'max_players': status.players.max,
                'auth_mode': auth_mode,
                'version': str(status.version.name),
                'description': str(status.description)[:200],
                'status': 'online',
                'last_seen': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return None
    
    def phase1_quick_scan(self, ips: List[str], workers: int = 200):
        """Phase 1: Quick scan all IPs"""
        print(f"\n🚀 PHASE 1: Quick Scan ({len(ips)} servers)")
        print(f"   Workers: {workers}, Timeout: 3s")
        print("=" * 60)
        
        online_servers = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.quick_check, ip): ip for ip in ips}
            
            for future in tqdm(as_completed(futures), total=len(futures), 
                             desc="Quick scan", unit="srv"):
                try:
                    result = future.result()
                    if result and result.get('status') == 'online':
                        online_servers.append(result)
                except:
                    pass
        
        print(f"\n✓ Found {len(online_servers)} online servers")
        return online_servers
    
    def phase2_full_scan(self, servers: List[Dict], workers: int = 100):
        """Phase 2: Full scan only online servers"""
        print(f"\n🔍 PHASE 2: Full Scan ({len(servers)} online servers)")
        print(f"   Workers: {workers}")
        print("=" * 60)
        
        verified_servers = []
        premium_servers = []
        non_premium_servers = []
        
        # Extract IPs
        ips = [s['ip'] for s in servers]
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.full_scan, ip): ip for ip in ips}
            
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc="Full scan", unit="srv"):
                try:
                    result = future.result()
                    if result:
                        verified_servers.append(result)
                        
                        # Categorize
                        if result.get('auth_mode') == 'PREMIUM' and result.get('online', 0) >= 500:
                            premium_servers.append(result)
                            tqdm.write(f"✓ Premium: {result['ip']} - {result['online']} players")
                        elif result.get('online', 0) > 0:
                            non_premium_servers.append(result)
                except:
                    pass
        
        return {
            'all': verified_servers,
            'premium': premium_servers,
            'non_premium': non_premium_servers
        }
    
    def save_results(self, results: Dict):
        """Save scan results"""
        # Save all verified servers
        all_file = self.data_dir / 'verified_servers.json'
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(results['all'], f, indent=2, ensure_ascii=False)
        
        # Update large_premium_servers.json
        if results['premium']:
            premium_file = self.data_dir / 'large_premium_servers.json'
            
            # Load existing
            existing = []
            if premium_file.exists():
                with open(premium_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            # Merge (avoid duplicates by IP)
            existing_ips = {s['ip'] for s in existing}
            for server in results['premium']:
                if server['ip'] not in existing_ips:
                    existing.append(server)
            
            # Save
            with open(premium_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Updated premium servers: {len(existing)} total")
        
        print(f"✓ Saved all results to {all_file}")
    
    def run(self, source_file: str):
        """Run complete optimized scan"""
        # Load IPs
        source_path = self.data_dir / source_file
        with open(source_path, 'r') as f:
            ips = [line.strip() for line in f if line.strip()]
        
        print(f"\n{'='*60}")
        print(f"  FAST SERVER SCANNER")
        print(f"{'='*60}")
        print(f"Total IPs to scan: {len(ips)}")
        
        # Phase 1: Quick scan
        online_servers = self.phase1_quick_scan(ips, workers=200)
        
        if not online_servers:
            print("\n❌ No online servers found")
            return
        
        # Phase 2: Full scan
        results = self.phase2_full_scan(online_servers, workers=100)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"  Total Online: {len(results['all'])}")
        print(f"  Premium (500+): {len(results['premium'])}")
        print(f"  Non-Premium: {len(results['non_premium'])}")
        
        # Top servers
        if results['premium']:
            print(f"\n🏆 Top Premium Servers:")
            top = sorted(results['premium'], key=lambda x: x.get('online', 0), reverse=True)[:10]
            for i, srv in enumerate(top, 1):
                print(f"  {i:2}. {srv['ip']:35} {srv.get('online', 0):>6} players")
        
        # Save
        self.save_results(results)
        
        return results

if __name__ == "__main__":
    scanner = FastScanner()
    scanner.run('all_ips_for_scan.txt')
