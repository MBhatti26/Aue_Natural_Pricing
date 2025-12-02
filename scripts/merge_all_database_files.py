#!/usr/bin/env python3
"""
Merge ALL historical database files into one central database
- Combines all archived database files
- Merges with current database files
- Creates comprehensive master database files
"""

import os
import pandas as pd
import glob
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_IMPORT_DIR = PROJECT_ROOT / 'database_to_import'
ARCHIVE_DIR = DB_IMPORT_DIR / 'archive'

def merge_all_files(file_type, output_filename):
    """Merge all files of a given type (product, brand, etc.)"""
    print(f"\n📋 Merging {file_type} files...")
    
    # Find all files matching the pattern
    pattern = f"{file_type}_*.csv"
    
    # Get files from main dir
    main_files = list(DB_IMPORT_DIR.glob(pattern))
    # Get files from archive
    archive_files = list(ARCHIVE_DIR.glob(pattern))
    
    all_files = main_files + archive_files
    
    if not all_files:
        print(f"  ⚠️  No {file_type} files found")
        return None
    
    print(f"  📁 Found {len(all_files)} files to merge")
    
    dfs = []
    for file_path in all_files:
        try:
            df = pd.read_csv(file_path)
            print(f"     • {file_path.name}: {len(df)} rows")
            dfs.append(df)
        except Exception as e:
            print(f"     ❌ Error reading {file_path.name}: {e}")
    
    if not dfs:
        print(f"  ⚠️  No valid {file_type} dataframes to merge")
        return None
    
    # Concatenate all dataframes
    merged_df = pd.concat(dfs, ignore_index=True)
    print(f"  📊 Total rows before dedup: {len(merged_df)}")
    
    # Remove duplicates based on ID column
    id_columns = {
        'product': 'product_id',
        'brand': 'brand_id',
        'category': 'category_id',
        'retailer': 'retailer_id',
        'price_source': 'source_id',
        'price_history': 'price_id'
    }
    
    id_col = id_columns.get(file_type)
    if id_col and id_col in merged_df.columns:
        before_dedup = len(merged_df)
        merged_df = merged_df.drop_duplicates(subset=[id_col], keep='last')
        print(f"  🔄 Removed {before_dedup - len(merged_df)} duplicates (kept latest)")
    
    print(f"  ✅ Final merged rows: {len(merged_df)}")
    
    # Save merged file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = DB_IMPORT_DIR / f"{file_type}_{timestamp}.csv"
    merged_df.to_csv(output_path, index=False)
    print(f"  💾 Saved to: {output_path.name}")
    
    return merged_df

def main():
    print("🚀 MERGING ALL DATABASE FILES INTO CENTRAL REPOSITORY")
    print("=" * 60)
    
    # File types to merge
    file_types = ['brand', 'category', 'price_source', 'retailer', 'product', 'price_history']
    
    results = {}
    for file_type in file_types:
        df = merge_all_files(file_type, file_type)
        if df is not None:
            results[file_type] = len(df)
    
    print("\n" + "=" * 60)
    print("📊 MERGE SUMMARY")
    print("=" * 60)
    for file_type, count in results.items():
        print(f"  {file_type:15}: {count:,} records")
    
    print("\n✅ All database files merged successfully!")
    print(f"📁 Location: {DB_IMPORT_DIR}")
    print("\n🔄 Next steps:")
    print("  1. Run: python scripts/reload_postgres_db.py")
    print("  2. Run: python src/enhanced_matching_engine.py")

if __name__ == "__main__":
    main()
