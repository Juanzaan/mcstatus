import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.enterprise.verifier import EnterpriseVerifier

async def main():
    print("🚀 Starting Enterprise Engine Test...")
    
    # Test targets
    targets = [
        "mc.hypixel.net",          # Premium
        "play.universocraft.com",  # Semi-Premium (Known signature)
        "mc.minehut.com",          # Standard
        "blocksmc.com",            # Cracked/Semi
        "play.pika-network.net",   # Cracked
        "eu.minemen.club",
        "invalid.server.local",    # Offline
    ]
    
    # Add some duplicates to test concurrency
    targets.extend(["mc.hypixel.net"] * 5)
    
    verifier = EnterpriseVerifier(concurrency=10, timeout=3.0)
    results = await verifier.verify_batch(targets)
    
    print("\n📊 Results:")
    print("-" * 60)
    print(f"{'Target':<25} | {'Type':<15} | {'Latency':<8} | {'Players'}")
    print("-" * 60)
    
    for res in results:
        meta = res['metadata']
        print(f"{res['target']:<25} | {res['type']:<15} | {meta['latency']:<8} | {meta['players_online']}/{meta['players_max']}")
        
    print("-" * 60)

if __name__ == "__main__":
    # Fix for Windows asyncio loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
