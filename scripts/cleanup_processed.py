#!/usr/bin/env python3
"""
Processed Folder Cleanup Script

Maintains the data/processed/ folder with only the latest files from each date.
Moves older files to archive_old_files/ directory.
"""

import os
import glob
import shutil
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("cleanup")

PROCESSED_DIR = "data/processed"
ARCHIVE_DIR = "data/processed/archive_old_files"

def get_file_date(filepath):
    """Extract date from timestamped filename."""
    try:
        filename = os.path.basename(filepath)
        # Extract YYYYMMDD from filename like processed_matches_20251118_155806.csv
        parts = filename.split('_')
        for part in parts:
            if len(part) == 8 and part.isdigit():
                return part
    except:
        pass
    return None

def cleanup_processed_folder():
    """Keep only the latest file for each date, archive the rest."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # File patterns to clean up
    patterns = [
        "processed_matches_*.csv",
        "unmatched_products_*.csv", 
        "processing_summary_*.json"
    ]
    
    for pattern in patterns:
        files = glob.glob(os.path.join(PROCESSED_DIR, pattern))
        
        # Group files by date
        date_groups = {}
        for filepath in files:
            file_date = get_file_date(filepath)
            if file_date:
                if file_date not in date_groups:
                    date_groups[file_date] = []
                date_groups[file_date].append(filepath)
        
        # For each date, keep only the latest file
        for date, file_list in date_groups.items():
            if len(file_list) > 1:
                # Sort by timestamp (full filename)
                file_list.sort()
                # Keep the latest, archive the rest
                for filepath in file_list[:-1]:
                    filename = os.path.basename(filepath)
                    archive_path = os.path.join(ARCHIVE_DIR, filename)
                    log.info(f"Archiving {filename} -> archive_old_files/")
                    shutil.move(filepath, archive_path)
                
                log.info(f"Kept latest {pattern.replace('*', date)}: {os.path.basename(file_list[-1])}")
    
    # Clean up any old CSV files that don't match our patterns
    old_patterns = [
        "brand_*.csv",
        "category_*.csv", 
        "price_*.csv",
        "product_*.csv",
        "retailer_*.csv",
        "*_enhanced_*.csv",
        "*_v*.csv",
        "best_match_*.csv",
        "matched_products_*.csv",
        "similar_matches_*.csv",
        "perfect_matches_*.csv",
        "matching_summary_*.json"
    ]
    
    for pattern in old_patterns:
        files = glob.glob(os.path.join(PROCESSED_DIR, pattern))
        for filepath in files:
            filename = os.path.basename(filepath)
            archive_path = os.path.join(ARCHIVE_DIR, filename)
            log.info(f"Archiving old format file: {filename}")
            shutil.move(filepath, archive_path)
    
    # Summary
    remaining_files = []
    for pattern in ["*.csv", "*.json"]:
        remaining_files.extend(glob.glob(os.path.join(PROCESSED_DIR, pattern)))
    
    # Exclude cache and archive folder
    remaining_files = [f for f in remaining_files 
                      if not f.endswith('.pkl') 
                      and 'archive_old_files' not in f]
    
    log.info(f"Cleanup completed. {len(remaining_files)} files remaining in processed/")
    for filepath in remaining_files:
        log.info(f"  - {os.path.basename(filepath)}")

def main():
    """Main cleanup function."""
    log.info("Starting processed folder cleanup...")
    
    if not os.path.exists(PROCESSED_DIR):
        log.error(f"Processed directory not found: {PROCESSED_DIR}")
        return
    
    cleanup_processed_folder()
    log.info("Processed folder cleanup completed.")

if __name__ == "__main__":
    main()
