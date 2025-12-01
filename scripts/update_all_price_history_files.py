#!/usr/bin/env python3
"""
Update All Price History Files with date_key
--------------------------------------------
This script updates ALL price_history CSV files (current and archived)
to add the date_key column. It also generates a comprehensive date_dim
table covering all dates found across all files.

Usage:
    python scripts/update_all_price_history_files.py
"""

import sys
import os
import pandas as pd
import logging
from pathlib import Path
import glob

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from date_utils import parse_date_key, generate_date_dim_entries

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
DATABASE_DIR = Path(__file__).parent.parent / 'database_to_import'
OUTPUT_DATE_DIM_FILE = DATABASE_DIR / 'date_dim.csv'


def find_all_price_history_files():
    """Find all price_history CSV files (current and archived)."""
    files = []
    
    # Current file
    current_pattern = str(DATABASE_DIR / 'price_history*.csv')
    files.extend(glob.glob(current_pattern))
    
    # Archived files
    archive_pattern = str(DATABASE_DIR / 'archive' / 'price_history*.csv')
    files.extend(glob.glob(archive_pattern))
    
    return sorted(files)


def extract_all_dates(file_paths):
    """Extract all unique dates from all price_history files."""
    all_date_keys = set()
    file_stats = []
    
    for file_path in file_paths:
        logger.info(f"Processing: {Path(file_path).name}")
        
        try:
            df = pd.read_csv(file_path)
            
            if 'date_collected' not in df.columns:
                logger.warning(f"  ⚠ No date_collected column in {Path(file_path).name}")
                continue
            
            # Parse dates
            df['date_key'] = df['date_collected'].apply(parse_date_key)
            
            # Remove nulls
            df_valid = df[df['date_key'].notna()]
            
            if len(df_valid) == 0:
                logger.warning(f"  ⚠ No valid dates in {Path(file_path).name}")
                continue
            
            # Collect unique dates
            file_dates = set(df_valid['date_key'].astype(int).unique())
            all_date_keys.update(file_dates)
            
            min_date = int(df_valid['date_key'].min())
            max_date = int(df_valid['date_key'].max())
            
            logger.info(f"  ✓ {len(df_valid)} records, dates: {min_date} to {max_date}")
            
            file_stats.append({
                'file': Path(file_path).name,
                'records': len(df_valid),
                'min_date': min_date,
                'max_date': max_date,
                'unique_dates': len(file_dates)
            })
            
        except Exception as e:
            logger.error(f"  ✗ Error processing {Path(file_path).name}: {e}")
    
    return all_date_keys, file_stats


def update_single_file(file_path):
    """Update a single price_history file with date_key column."""
    try:
        df = pd.read_csv(file_path)
        
        # Check if date_key already exists
        if 'date_key' in df.columns:
            logger.info(f"  ⊙ Already has date_key: {Path(file_path).name}")
            return True
        
        # Add date_key
        df['date_key'] = df['date_collected'].apply(parse_date_key)
        
        # Reorder columns
        columns = list(df.columns)
        columns.remove('date_key')
        date_col_idx = columns.index('date_collected')
        columns.insert(date_col_idx + 1, 'date_key')
        df = df[columns]
        
        # Backup original
        backup_path = file_path.replace('.csv', '.backup.csv')
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy(file_path, backup_path)
            logger.info(f"  📦 Backup created: {Path(backup_path).name}")
        
        # Save updated file
        df.to_csv(file_path, index=False)
        logger.info(f"  ✓ Updated: {Path(file_path).name}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ Error updating {Path(file_path).name}: {e}")
        return False


def main():
    """Main execution function."""
    logger.info("="*70)
    logger.info("Update All Price History Files with date_key")
    logger.info("="*70)
    
    # Step 1: Find all files
    logger.info("\n[1/4] Finding all price_history CSV files...")
    files = find_all_price_history_files()
    logger.info(f"Found {len(files)} files")
    
    # Step 2: Extract all dates
    logger.info("\n[2/4] Extracting dates from all files...")
    all_dates, file_stats = extract_all_dates(files)
    
    if not all_dates:
        logger.error("No valid dates found. Exiting.")
        return 1
    
    logger.info(f"\nFound {len(all_dates)} unique dates across all files")
    
    # Step 3: Generate comprehensive date_dim
    logger.info("\n[3/4] Generating comprehensive date dimension...")
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    logger.info(f"Date range: {min_date} to {max_date}")
    
    entries = generate_date_dim_entries(min_date, max_date)
    df_date_dim = pd.DataFrame(entries)
    
    df_date_dim.to_csv(OUTPUT_DATE_DIM_FILE, index=False)
    logger.info(f"✓ Saved {len(df_date_dim)} date dimension entries to {OUTPUT_DATE_DIM_FILE.name}")
    
    # Step 4: Update all files with date_key
    logger.info("\n[4/4] Updating all price_history files with date_key...")
    success_count = 0
    for file_path in files:
        if update_single_file(file_path):
            success_count += 1
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✓ Update Complete")
    logger.info("="*70)
    logger.info(f"Files processed: {len(files)}")
    logger.info(f"Files updated: {success_count}")
    logger.info(f"Date dimension records: {len(df_date_dim)}")
    logger.info(f"Date range: {min_date} to {max_date}")
    
    logger.info("\n📊 File Statistics:")
    for stat in file_stats:
        logger.info(f"  {stat['file']:45} {stat['records']:5} records  "
                   f"{stat['min_date']} to {stat['max_date']}  "
                   f"({stat['unique_dates']} unique dates)")
    
    logger.info("\n✓ All price_history files now have date_key column")
    logger.info(f"✓ Comprehensive date_dim saved to {OUTPUT_DATE_DIM_FILE.name}")
    logger.info("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
