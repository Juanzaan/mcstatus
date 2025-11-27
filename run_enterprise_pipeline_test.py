"""
Quick test of Enterprise Pipeline with a small sample
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.enterprise.verifier import EnterpriseVerifier

async def main():
    print("🧪 Testing Enterprise Pipeline with sample data...")
    
    # Small test set
    test_servers = [
        "mc.hypixel.net",
        "play.universocraft.com",
        "mc.minehut.com",
        "play.pika-network.net",
        "blocksmc.com",
    ]
    
    verifier = EnterpriseVerifier(concurrency=5, timeout=5.0)
    results = await verifier.verify_batch(test_servers)
    
    # Process results
    categorized = {
        "premium": [],
        "semi_premium": [],
        "non_premium": [],
        "offline": []
    }
    
    for res in results:
        server_type = res['type'].lower()
        meta = res['metadata']
        
        entry = {
            "target": res['target'],
            "type": res['type'],
            "players": f"{meta['players_online']}/{meta['players_max']}",
            "version": meta['version'],
            "latency": round(meta['latency'], 2)
        }
        
        if server_type == "premium":
            categorized["premium"].append(entry)
        elif server_type == "semi_premium":
            categorized["semi_premium"].append(entry)
        elif server_type == "non_premium":
            categorized["non_premium"].append(entry)
        else:
            categorized["offline"].append(entry)
    
    # Display results
    print("\n" + "="*60)
    print("RESULTS BY CATEGORY")
    print("="*60)
    
    for category, servers in categorized.items():
        if servers:
            print(f"\n🔹 {category.upper().replace('_', '-')} ({len(servers)}):")
            for s in servers:
                print(f"  • {s['target']}: {s['players']} players, v{s['version']}, {s['latency']}ms")
    
    print("\n" + "="*60)
    print(f"✅ Test Complete!")
    print(f"   Premium: {len(categorized['premium'])}")
    print(f"   Semi-Premium: {len(categorized['semi_premium'])}")
    print(f"   Non-Premium: {len(categorized['non_premium'])}")
    print(f"   Offline: {len(categorized['offline'])}")
    print("="*60)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
