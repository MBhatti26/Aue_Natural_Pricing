#!/usr/bin/env python3
"""
Process ALL cleaned intermediate files and merge into comprehensive database
"""

import pandas as pd
import hashlib
import glob
from pathlib import Path
from datetime import datetime

INTERMEDIATE_DIR = Path("data/processed/intermediate")
OUTPUT_DIR = Path("database_to_import")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_id(prefix, value):
    """Generate a consistent ID from a value"""
    if pd.isna(value) or str(value).strip() == "":
        return None
    hash_val = hashlib.md5(str(value).lower().encode()).hexdigest()[:8]
    return f"{prefix}{hash_val}"

print("🚀 Processing ALL cleaned files into comprehensive database")
print("=" * 60)

# Find all cleaned files
cleaned_files = sorted(glob.glob(str(INTERMEDIATE_DIR / "cleaned_products_*.csv")))
print(f"📁 Found {len(cleaned_files)} cleaned files:")
for f in cleaned_files:
    print(f"   • {Path(f).name}")

# Process each file and collect dataframes
all_brands = []
all_categories = []
all_retailers = []
all_products = []
all_price_history = []

price_id_counter = 1

for file_path in cleaned_files:
    print(f"\n📋 Processing: {Path(file_path).name}")
    df = pd.read_csv(file_path)
    print(f"   📊 Rows: {len(df)}")
    
    # Extract brands
    brands = df[['brand_clean']].dropna().drop_duplicates()
    brands['brand_id'] = brands['brand_clean'].apply(lambda x: generate_id('BRD', x))
    brands = brands.rename(columns={'brand_clean': 'brand_name'})
    all_brands.append(brands[['brand_id', 'brand_name']])
    
    # Extract categories
    categories = df[['category_clean']].dropna().drop_duplicates()
    categories['category_id'] = categories['category_clean'].apply(lambda x: generate_id('CAT', x))
    categories = categories.rename(columns={'category_clean': 'category_name'})
    all_categories.append(categories[['category_id', 'category_name']])
    
    # Extract retailers
    retailers = df[['merchant']].dropna().drop_duplicates()
    retailers['retailer_id'] = retailers['merchant'].apply(lambda x: generate_id('RET', x))
    retailers['source_id'] = 'SRC00000001'
    retailers = retailers.rename(columns={'merchant': 'retailer_name'})
    all_retailers.append(retailers[['retailer_id', 'source_id', 'retailer_name']])
    
    # Extract products
    products = df[['title', 'brand_clean', 'category_clean', 'size_value', 'size_unit']].copy()
    products['product_id'] = products['title'].apply(lambda x: generate_id('PRD', x))
    products['brand_id'] = products['brand_clean'].apply(lambda x: generate_id('BRD', x))
    products['category_id'] = products['category_clean'].apply(lambda x: generate_id('CAT', x))
    products = products.rename(columns={'title': 'product_name'})
    all_products.append(products[['product_id', 'product_name', 'brand_id', 'category_id', 'size_value', 'size_unit']])
    
    # Extract price history
    price_history = df[['title', 'merchant', 'price', 'currency', 'timestamp', 'url', 'thumbnail']].copy()
    price_history['product_id'] = price_history['title'].apply(lambda x: generate_id('PRD', x))
    price_history['retailer_id'] = price_history['merchant'].apply(lambda x: generate_id('RET', x))
    price_history = price_history.rename(columns={'timestamp': 'date_collected'})
    
    # Generate sequential price_ids
    price_history['price_id'] = [f"PRC{str(price_id_counter + i).zfill(8)}" for i in range(len(price_history))]
    price_id_counter += len(price_history)
    
    # Generate date_key
    price_history['date_key'] = price_history['date_collected'].apply(
        lambda x: int(str(x).split('_')[0]) if pd.notna(x) else None
    )
    
    price_history['discount'] = None
    all_price_history.append(price_history[['price_id', 'product_id', 'retailer_id', 'price', 'discount', 
                                            'currency', 'date_collected', 'date_key', 'url', 'thumbnail']])

print("\n" + "=" * 60)
print("📊 Merging and deduplicating...")

# Merge all dataframes
merged_brands = pd.concat(all_brands, ignore_index=True).drop_duplicates(subset=['brand_id'])
merged_categories = pd.concat(all_categories, ignore_index=True).drop_duplicates(subset=['category_id'])
merged_retailers = pd.concat(all_retailers, ignore_index=True).drop_duplicates(subset=['retailer_id'])
merged_products = pd.concat(all_products, ignore_index=True).drop_duplicates(subset=['product_id'])
merged_price_history = pd.concat(all_price_history, ignore_index=True).drop_duplicates(subset=['price_id'])

print(f"   • Brands: {len(merged_brands)} unique")
print(f"   • Categories: {len(merged_categories)} unique")
print(f"   • Retailers: {len(merged_retailers)} unique")
print(f"   • Products: {len(merged_products)} unique")
print(f"   • Price History: {len(merged_price_history)} total records")

# Price source
price_source = pd.DataFrame([{
    'source_id': 'SRC00000001',
    'source_name': 'Oxylabs Google Shopping',
    'region': 'GB'
}])

# Save all files
print(f"\n💾 Saving to {OUTPUT_DIR}...")

price_source.to_csv(OUTPUT_DIR / f"price_source_{TIMESTAMP}.csv", index=False)
merged_brands.to_csv(OUTPUT_DIR / f"brand_{TIMESTAMP}.csv", index=False)
merged_categories.to_csv(OUTPUT_DIR / f"category_{TIMESTAMP}.csv", index=False)
merged_retailers.to_csv(OUTPUT_DIR / f"retailer_{TIMESTAMP}.csv", index=False)
merged_products.to_csv(OUTPUT_DIR / f"product_{TIMESTAMP}.csv", index=False)
merged_price_history.to_csv(OUTPUT_DIR / f"price_history_{TIMESTAMP}.csv", index=False)

print(f"   ✅ All files saved with timestamp: {TIMESTAMP}")
print("\n✅ Comprehensive database created from ALL historical data!")
print(f"\n🔄 Next: Run 'python scripts/reload_postgres_db.py' to load into PostgreSQL")
