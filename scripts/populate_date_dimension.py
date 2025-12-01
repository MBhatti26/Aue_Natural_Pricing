#!/usr/bin/env python3
"""
Populate Date Dimension Table
-----------------------------
This script populates the date_dim table with date entries derived from
the price_history.date_collected field. It also updates price_history records
to set the date_key foreign key.

Usage:
    python scripts/populate_date_dimension.py
"""

import sys
import os
import pandas as pd
import logging
from pathlib import Path

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
PRICE_HISTORY_FILE = DATABASE_DIR / 'price_history_20251108_121845.csv'
OUTPUT_DATE_DIM_FILE = DATABASE_DIR / 'date_dim.csv'


def extract_date_range_from_price_history(csv_path):
    """
    Read price_history CSV and determine the date range needed for date_dim.
    
    Returns:
        tuple: (min_date_key, max_date_key)
    """
    logger.info(f"Reading price history from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    if 'date_collected' not in df.columns:
        logger.error("date_collected column not found in price_history CSV")
        return None, None
    
    logger.info(f"Found {len(df)} price history records")
    
    # Parse all date_collected values
    df['date_key'] = df['date_collected'].apply(parse_date_key)
    
    # Remove any failed parses
    df_valid = df[df['date_key'].notna()]
    failed_count = len(df) - len(df_valid)
    
    if failed_count > 0:
        logger.warning(f"Failed to parse {failed_count} dates")
    
    if len(df_valid) == 0:
        logger.error("No valid dates found in price_history")
        return None, None
    
    min_date = int(df_valid['date_key'].min())
    max_date = int(df_valid['date_key'].max())
    
    logger.info(f"Date range: {min_date} to {max_date}")
    
    return min_date, max_date


def generate_and_save_date_dim(min_date_key, max_date_key, output_path):
    """
    Generate date dimension entries and save to CSV.
    """
    logger.info(f"Generating date dimension entries from {min_date_key} to {max_date_key}...")
    
    entries = generate_date_dim_entries(min_date_key, max_date_key)
    
    logger.info(f"Generated {len(entries)} date dimension entries")
    
    # Convert to DataFrame
    df_date_dim = pd.DataFrame(entries)
    
    # Save to CSV
    df_date_dim.to_csv(output_path, index=False)
    logger.info(f"✓ Saved date dimension to {output_path}")
    
    # Show sample
    logger.info(f"\nSample entries:")
    logger.info(f"\n{df_date_dim.head(10).to_string()}")
    
    return df_date_dim


def update_price_history_with_date_key(input_path, output_path=None):
    """
    Read price_history CSV, add date_key column, and save back.
    
    Args:
        input_path: Path to input price_history CSV
        output_path: Path to save updated CSV (if None, overwrites input)
    """
    if output_path is None:
        output_path = input_path
    
    logger.info(f"Updating price_history with date_key...")
    df = pd.read_csv(input_path)
    
    # Add date_key column
    df['date_key'] = df['date_collected'].apply(parse_date_key)
    
    # Check for any nulls
    null_count = df['date_key'].isna().sum()
    if null_count > 0:
        logger.warning(f"⚠ {null_count} records have null date_key (invalid dates)")
    
    # Reorder columns to place date_key after date_collected
    columns = list(df.columns)
    if 'date_key' in columns:
        columns.remove('date_key')
    
    # Insert date_key after date_collected
    date_col_idx = columns.index('date_collected')
    columns.insert(date_col_idx + 1, 'date_key')
    
    df = df[columns]
    
    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"✓ Updated price_history saved to {output_path}")
    
    return df


def main():
    """Main execution function."""
    logger.info("="*60)
    logger.info("Date Dimension Population Script")
    logger.info("="*60)
    
    # Step 1: Extract date range from price_history
    min_date, max_date = extract_date_range_from_price_history(PRICE_HISTORY_FILE)
    
    if min_date is None or max_date is None:
        logger.error("Failed to extract date range. Exiting.")
        return 1
    
    # Step 2: Generate and save date_dim
    df_date_dim = generate_and_save_date_dim(min_date, max_date, OUTPUT_DATE_DIM_FILE)
    
    # Step 3: Update price_history with date_key
    df_price_history = update_price_history_with_date_key(PRICE_HISTORY_FILE)
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("✓ Date Dimension Population Complete")
    logger.info("="*60)
    logger.info(f"Date dimension records: {len(df_date_dim)}")
    logger.info(f"Price history records: {len(df_price_history)}")
    logger.info(f"Date range: {min_date} to {max_date}")
    logger.info(f"\nOutputs:")
    logger.info(f"  - {OUTPUT_DATE_DIM_FILE}")
    logger.info(f"  - {PRICE_HISTORY_FILE} (updated with date_key)")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
