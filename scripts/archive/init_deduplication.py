#!/usr/bin/env python3
"""
Initialize Deduplication State from Historical Data
Run this once to analyze existing CSV files and build the deduplication state
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from deduplication_manager import DeduplicationManager

def main():
    print("🏗️  Initializing Deduplication State from Historical Data")
    print("=" * 60)
    
    # Create deduplication manager
    project_root = os.path.dirname(os.path.dirname(__file__))  # Go up two levels to project root
    dedup_manager = DeduplicationManager(project_root)
    
    # Show current stats
    stats = dedup_manager.get_deduplication_stats()
    print("📊 Current State:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # Analyze historical data
    dedup_manager.analyze_historical_data()
    
    # Show updated stats
    stats = dedup_manager.get_deduplication_stats()
    print("\n📊 Updated State:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Deduplication state initialized successfully!")
    print("🚀 Future extractions will now filter out previously seen products")

if __name__ == "__main__":
    main()
