#!/usr/bin/env python3
"""
Simple script to copy the latest processed files to database_to_import directory
"""

import os
import glob
import shutil

def update_database_files():
    """Copy latest processed files to database import directory"""
    
    processed_dir = "data/processed"
    import_dir = "database_to_import"
    
    # Find latest timestamp
    pattern = os.path.join(processed_dir, "*_????????_??????.csv")
    files = glob.glob(pattern)
    
    if not files:
        print("❌ No processed files found")
        return False
    
    # Extract latest timestamp
    timestamps = set()
    for file in files:
        basename = os.path.basename(file)
        parts = basename.split('_')
        if len(parts) >= 3:
            timestamp = f"{parts[-2]}_{parts[-1].replace('.csv', '')}"
            timestamps.add(timestamp)
    
    latest_timestamp = max(timestamps)
    print(f"📅 Using latest timestamp: {latest_timestamp}")
    
    # File mappings
    file_mappings = [
        (f"brand_{latest_timestamp}.csv", "brand_name.csv"),
        (f"category_{latest_timestamp}.csv", "category_name.csv"),
        (f"price_source_{latest_timestamp}.csv", "price_source.csv"),
        (f"retailer_{latest_timestamp}.csv", "retailer_name.csv"),
        (f"product_{latest_timestamp}.csv", "product.csv"),
        (f"price_history_{latest_timestamp}.csv", "price_history.csv")
    ]
    
    print("📋 Copying files...")
    for source_file, target_file in file_mappings:
        source_path = os.path.join(processed_dir, source_file)
        target_path = os.path.join(import_dir, target_file)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, target_path)
            print(f"  ✅ {source_file} → {target_file}")
        else:
            print(f"  ❌ {source_file} not found")
    
    print("🎉 Database files updated!")
    return True

if __name__ == "__main__":
    update_database_files()
