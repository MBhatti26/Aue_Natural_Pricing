#!/usr/bin/env python3
"""
Backfill Date Fields in Existing Match Files
--------------------------------------------
Adds date_collected and date_key columns to existing processed_matches.csv
and FINAL_MATCHES.csv files by looking up the product IDs in the database.

This ensures backward compatibility when merging old and new matching results.
"""

import sys
import os
import pandas as pd
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from date_utils import parse_date_key

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
DATA_DIR = Path(__file__).parent.parent / 'data' / 'processed'
DATABASE_DIR = Path(__file__).parent.parent / 'database_to_import'

# Files to update
MATCH_FILES = [
    DATA_DIR / 'processed_matches.csv',
    DATA_DIR / 'FINAL_MATCHES.csv'
]


def load_product_date_mapping():
    """Load product_id → (date_collected, date_key) mapping from price_history."""
    logger.info("Loading product date mappings from price_history files...")
    
    # Find all price_history files
    import glob
    ph_files = glob.glob(str(DATABASE_DIR / 'price_history*.csv'))
    ph_files.extend(glob.glob(str(DATABASE_DIR / 'archive' / 'price_history*.csv')))
    
    logger.info(f"Found {len(ph_files)} price_history files")
    
    mapping = {}
    
    for file_path in ph_files:
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                product_id = row['product_id']
                date_collected = row.get('date_collected', '')
                date_key = row.get('date_key', None)
                
                # Only store if we don't have it yet (keep earliest date)
                if product_id not in mapping:
                    mapping[product_id] = {
                        'date_collected': date_collected,
                        'date_key': date_key
                    }
        
        except Exception as e:
            logger.warning(f"Error loading {Path(file_path).name}: {e}")
    
    logger.info(f"Loaded date info for {len(mapping)} products")
    return mapping


def backfill_match_file(file_path, product_date_mapping):
    """Add date columns to a match file."""
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False
    
    logger.info(f"\nProcessing: {file_path.name}")
    
    try:
        df = pd.read_csv(file_path)
        
        # Check if already has date fields
        if 'date_collected_1' in df.columns and 'date_key_1' in df.columns:
            logger.info("  ⊙ Already has date fields")
            return True
        
        logger.info(f"  Found {len(df)} matches")
        
        # Add date columns
        df['date_collected_1'] = df['product_1_id'].map(lambda pid: product_date_mapping.get(pid, {}).get('date_collected', ''))
        df['date_collected_2'] = df['product_2_id'].map(lambda pid: product_date_mapping.get(pid, {}).get('date_collected', ''))
        df['date_key_1'] = df['product_1_id'].map(lambda pid: product_date_mapping.get(pid, {}).get('date_key', None))
        df['date_key_2'] = df['product_2_id'].map(lambda pid: product_date_mapping.get(pid, {}).get('date_key', None))
        
        # Reorder columns to put date fields after currency
        cols = list(df.columns)
        
        # Remove date columns
        date_cols = ['date_collected_1', 'date_collected_2', 'date_key_1', 'date_key_2']
        for col in date_cols:
            cols.remove(col)
        
        # Insert after currency_2
        if 'currency_2' in cols:
            insert_idx = cols.index('currency_2') + 1
            for col in reversed(date_cols):
                cols.insert(insert_idx, col)
        else:
            # If no currency_2, append at end
            cols.extend(date_cols)
        
        df = df[cols]
        
        # Backup original
        backup_path = str(file_path).replace('.csv', '.pre_date_backfill.csv')
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy(file_path, backup_path)
            logger.info(f"  📦 Backup created: {Path(backup_path).name}")
        
        # Save updated file
        df.to_csv(file_path, index=False)
        logger.info(f"  ✓ Updated with date fields")
        
        # Report coverage
        has_date_1 = df['date_collected_1'].notna().sum()
        has_date_2 = df['date_collected_2'].notna().sum()
        logger.info(f"  Coverage: {has_date_1}/{len(df)} product_1, {has_date_2}/{len(df)} product_2")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ Error: {e}")
        return False


def main():
    """Main execution function."""
    logger.info("="*70)
    logger.info("Backfill Date Fields in Existing Match Files")
    logger.info("="*70)
    
    # Step 1: Load product date mappings
    product_date_mapping = load_product_date_mapping()
    
    if not product_date_mapping:
        logger.error("No product date mappings found. Exiting.")
        return 1
    
    # Step 2: Update match files
    logger.info("\nUpdating match files...")
    success_count = 0
    
    for file_path in MATCH_FILES:
        if backfill_match_file(file_path, product_date_mapping):
            success_count += 1
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✓ Backfill Complete")
    logger.info("="*70)
    logger.info(f"Files processed: {len(MATCH_FILES)}")
    logger.info(f"Files updated: {success_count}")
    logger.info("\n✓ Existing match files now have date_collected and date_key columns")
    logger.info("✓ Ready for merging with new matching results")
    logger.info("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
