"""
Master Deduplication CLI
Unified interface for all deduplication operations.

Usage:
    python scripts/master_dedup.py --mode dry-run
    python scripts/master_dedup.py --mode interactive --threshold 0.5
    python scripts/master_dedup.py --mode auto --threshold 0.9
"""

import argparse
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.deduplication_engine import DeduplicationService

def dry_run_mode(service: DeduplicationService, output_file: str = None):
    """Run analysis and generate report without changing DB"""
    print("=" * 60)
    print("DRY-RUN MODE")
    print("=" * 60)
    print()
    
    report = service.analyze()
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {output_file}")
    else:
        print("\n📊 MATCHES:")
        for match in report['matches'][:20]:  # Show first 20
            print(f"  {match['alias']} → {match['master']}")
            print(f"    Confidence: {match['confidence']:.0%} | Method: {match['method']}")
            print(f"    Reason: {match['reason']}")
            print()
        
        if len(report['matches']) > 20:
            print(f"  ... and {len(report['matches']) - 20} more matches")
    
    return report

def interactive_mode(service: DeduplicationService, threshold: float = 0.5):
    """Ask user for approval on medium-confidence matches"""
    print("=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print()
    
    report = service.analyze()
    
    # Filter by threshold
    matches = [m for m in report['matches'] if m['confidence'] >= threshold]
    
    print(f"Found {len(matches)} matches above {threshold:.0%} confidence")
    print()
    
    approved = []
    
    for i, match_data in enumerate(matches, 1):
        print(f"\n[{i}/{len(matches)}]")
        print(f"  Alias: {match_data['alias']}")
        print(f"  Master: {match_data['master']}")
        print(f"  Confidence: {match_data['confidence']:.0%}")
        print(f"  Method: {match_data['method']}")
        print(f"  Reason: {match_data['reason']}")
        
        while True:
            choice = input("\n  Merge? [Y/n/q]: ").strip().lower()
            if choice in ['y', '']:
                approved.append(match_data)
                print("  ✅ Approved")
                break
            elif choice == 'n':
                print("  ⏭️  Skipped")
                break
            elif choice == 'q':
                print("\n🛑 Aborted by user")
                return
    
    if approved:
        print(f"\n🔄 Merging {len(approved)} approved matches...")
        
        # Convert dicts to DuplicateMatch objects
        from core.deduplication_engine import DuplicateMatch
        match_objects = [
            DuplicateMatch(
                master_ip=m['master'],
                alias_ip=m['alias'],
                confidence=m['confidence'],
                detection_method=m['method'],
                reason=m['reason']
            ) for m in approved
        ]
        
        # Execute merge
        service.merge(match_objects, dry_run=False)
    else:
        print("\n✅ No matches approved")

def auto_merge_mode(service: DeduplicationService, threshold: float = 0.9):
    """Automatically merge high-confidence matches"""
    print("=" * 60)
    print("AUTO-MERGE MODE")
    print(f"Threshold: {threshold:.0%}")
    print("=" * 60)
    print()
    
    report = service.analyze()
    
    # Filter by threshold
    high_conf_matches = [m for m in report['matches'] if m['confidence'] >= threshold]
    
    print(f"Found {len(high_conf_matches)} matches above {threshold:.0%} confidence")
    
    if len(high_conf_matches) == 0:
        print("✅ No matches to merge")
        return
    
    confirm = input(f"\n⚠️  Proceed with merging {len(high_conf_matches)} aliases? [y/N]: ").strip().lower()
    
    if confirm != 'y':
        print("🛑 Aborted")
        return
    
    print("\n🔄 Merging...")
    
    # Convert dicts to DuplicateMatch objects
    from core.deduplication_engine import DuplicateMatch
    match_objects = [
        DuplicateMatch(
            master_ip=m['master'],
            alias_ip=m['alias'],
            confidence=m['confidence'],
            detection_method=m['method'],
            reason=m['reason']
        ) for m in high_conf_matches
    ]
    
    # Execute merge
    service.merge(match_objects, dry_run=False)

def main():
    parser = argparse.ArgumentParser(
        description="Unified Deduplication CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run analysis with JSON output
  python scripts/master_dedup.py --mode dry-run --output report.json
  
  # Interactive approval for medium-confidence matches
  python scripts/master_dedup.py --mode interactive --threshold 0.5
  
  # Auto-merge high-confidence matches only
  python scripts/master_dedup.py --mode auto --threshold 0.9
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['dry-run', 'interactive', 'auto'],
        required=True,
        help='Execution mode'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.5,
        help='Minimum confidence threshold (0.0-1.0)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for dry-run report (JSON)'
    )
    
    args = parser.parse_args()
    
    # Initialize service
    service = DeduplicationService()
    
    # Route to appropriate mode
    if args.mode == 'dry-run':
        dry_run_mode(service, args.output)
    elif args.mode == 'interactive':
        interactive_mode(service, args.threshold)
    elif args.mode == 'auto':
        auto_merge_mode(service, args.threshold)

if __name__ == "__main__":
    main()
