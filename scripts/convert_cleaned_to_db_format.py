#!/usr/bin/env python3
"""
Convert cleaned intermediate CSV to proper database import format
Creates: product, brand, category, retailer, price_history CSVs
"""

import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path

# Input file (cleaned data from Nov 25 extraction)
INPUT_FILE = "data/processed/intermediate/cleaned_products_20251202_105905.csv"
OUTPUT_DIR = Path("database_to_import")
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_id(prefix, value):
    """Generate a consistent ID from a value"""
    if pd.isna(value) or str(value).strip() == "":
        return None
    hash_val = hashlib.md5(str(value).lower().encode()).hexdigest()[:8]
    return f"{prefix}{hash_val}"

print("🚀 Converting cleaned data to database format...")
print(f"📁 Input: {INPUT_FILE}")

# Load cleaned data
df = pd.read_csv(INPUT_FILE)
print(f"📊 Loaded {len(df)} rows")

# Extract unique entities
print("\n📋 Extracting entities...")

# 1. PRICE SOURCE
price_source = pd.DataFrame([{
    'source_id': 'SRC00000001',
    'source_name': 'Oxylabs Google Shopping',
    'region': 'GB'
}])
print(f"   • price_source: {len(price_source)} rows")

# 2. BRANDS
brands = df[['brand_clean']].dropna().drop_duplicates()
brands['brand_id'] = brands['brand_clean'].apply(lambda x: generate_id('BRD', x))
brands = brands.rename(columns={'brand_clean': 'brand_name'})
brands = brands[['brand_id', 'brand_name']].drop_duplicates()
print(f"   • brands: {len(brands)} rows")

# 3. CATEGORIES
categories = df[['category_clean']].dropna().drop_duplicates()
categories['category_id'] = categories['category_clean'].apply(lambda x: generate_id('CAT', x))
categories = categories.rename(columns={'category_clean': 'category_name'})
categories = categories[['category_id', 'category_name']].drop_duplicates()
print(f"   • categories: {len(categories)} rows")

# 4. RETAILERS
retailers = df[['merchant']].dropna().drop_duplicates()
retailers['retailer_id'] = retailers['merchant'].apply(lambda x: generate_id('RET', x))
retailers['source_id'] = 'SRC00000001'
retailers = retailers.rename(columns={'merchant': 'retailer_name'})
retailers = retailers[['retailer_id', 'source_id', 'retailer_name']].drop_duplicates()
print(f"   • retailers: {len(retailers)} rows")

# 5. PRODUCTS
products = df[['title', 'brand_clean', 'category_clean', 'size_value', 'size_unit']].copy()
products['product_id'] = products['title'].apply(lambda x: generate_id('PRD', x))
products['brand_id'] = products['brand_clean'].apply(lambda x: generate_id('BRD', x))
products['category_id'] = products['category_clean'].apply(lambda x: generate_id('CAT', x))

products = products.rename(columns={'title': 'product_name'})
products = products[['product_id', 'product_name', 'brand_id', 'category_id', 'size_value', 'size_unit']]
products = products.drop_duplicates(subset=['product_id'])
print(f"   • products: {len(products)} rows")

# 6. PRICE HISTORY
price_history = df[['title', 'merchant', 'price', 'currency', 'timestamp', 'url', 'thumbnail']].copy()
price_history['price_id'] = [f"PRC{str(i+1).zfill(8)}" for i in range(len(price_history))]
price_history['product_id'] = price_history['title'].apply(lambda x: generate_id('PRD', x))
price_history['retailer_id'] = price_history['merchant'].apply(lambda x: generate_id('RET', x))
price_history = price_history.rename(columns={'timestamp': 'date_collected'})
price_history['discount'] = None

# Generate date_key from date_collected (format: YYYYMMDD_HHMMSS -> YYYYMMDD)
if 'date_collected' in price_history.columns:
    price_history['date_key'] = price_history['date_collected'].apply(
        lambda x: int(str(x).split('_')[0]) if pd.notna(x) else None
    )
else:
    price_history['date_key'] = int(TIMESTAMP.split('_')[0])

price_history = price_history[['price_id', 'product_id', 'retailer_id', 'price', 'discount', 
                                'currency', 'date_collected', 'date_key', 'url', 'thumbnail']]
print(f"   • price_history: {len(price_history)} rows")

# Save all files
print(f"\n💾 Saving to {OUTPUT_DIR}...")

price_source.to_csv(OUTPUT_DIR / f"price_source_{TIMESTAMP}.csv", index=False)
print(f"   ✅ price_source_{TIMESTAMP}.csv")

brands.to_csv(OUTPUT_DIR / f"brand_{TIMESTAMP}.csv", index=False)
print(f"   ✅ brand_{TIMESTAMP}.csv")

categories.to_csv(OUTPUT_DIR / f"category_{TIMESTAMP}.csv", index=False)
print(f"   ✅ category_{TIMESTAMP}.csv")

retailers.to_csv(OUTPUT_DIR / f"retailer_{TIMESTAMP}.csv", index=False)
print(f"   ✅ retailer_{TIMESTAMP}.csv")

products.to_csv(OUTPUT_DIR / f"product_{TIMESTAMP}.csv", index=False)
print(f"   ✅ product_{TIMESTAMP}.csv")

price_history.to_csv(OUTPUT_DIR / f"price_history_{TIMESTAMP}.csv", index=False)
print(f"   ✅ price_history_{TIMESTAMP}.csv")

print("\n✅ Conversion complete!")
print(f"\n🔄 Next: Run merge script to combine with existing data")
