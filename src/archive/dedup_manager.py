#!/usr/bin/env python3
"""
Deduplication Management Utility
Provides various operations for managing the deduplication system
"""

import sys
import os
import argparse

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from deduplication_manager import DeduplicationManager

def show_stats(dedup_manager):
    """Show deduplication statistics"""
    print("📊 Deduplication Statistics")
    print("-" * 30)
    
    stats = dedup_manager.get_deduplication_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

def analyze_file(dedup_manager, file_path):
    """Analyze a specific file for deduplication"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"🔍 Analyzing file: {os.path.basename(file_path)}")
    result_file, stats = dedup_manager.deduplicate_raw_data(file_path)
    
    print("\n📊 Deduplication Results:")
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value:,}")
    
    if result_file:
        print(f"\n💾 Deduplicated file saved: {os.path.basename(result_file)}")
    else:
        print("\n⚠️  No new products found - all were duplicates")

def reset_state(dedup_manager):
    """Reset deduplication state"""
    confirm = input("⚠️  This will reset all deduplication state. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        dedup_manager.reset_deduplication_state()
        print("✅ Deduplication state reset successfully")
    else:
        print("❌ Reset cancelled")

def initialize_from_historical(dedup_manager):
    """Initialize deduplication state from historical data"""
    print("🏗️  Initializing from historical data...")
    dedup_manager.analyze_historical_data()
    print("✅ Initialization complete")

def main():
    parser = argparse.ArgumentParser(description="Deduplication Management Utility")
    parser.add_argument('action', choices=['stats', 'analyze', 'reset', 'init'], 
                       help='Action to perform')
    parser.add_argument('--file', help='File to analyze (for analyze action)')
    
    args = parser.parse_args()
    
    # Get project root (go up one level from scripts directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dedup_manager = DeduplicationManager(project_root)
    
    print("🔧 Aue Natural Deduplication Manager")
    print("=" * 40)
    
    if args.action == 'stats':
        show_stats(dedup_manager)
    
    elif args.action == 'analyze':
        if not args.file:
            print("❌ --file argument required for analyze action")
            return
        analyze_file(dedup_manager, args.file)
    
    elif args.action == 'reset':
        reset_state(dedup_manager)
    
    elif args.action == 'init':
        initialize_from_historical(dedup_manager)

if __name__ == "__main__":
    main()
