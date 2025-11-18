import pandas as pd
import re
import json
import ast
import numpy as np
import logging
from datetime import datetime
import hashlib

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
KNOWN_BRANDS = [
    'Garnier', 'Friendly Soap', 'Kitsch', 'Faith in Nature', 
    'Davines', 'Soaphoria', 'weDo', 'Biovene', 'Little Soap Company',
    'Eco Warrior', 'LOOKFANTASTIC', 'Justmylook'
]

# === HELPER FUNCTIONS ===

def generate_id(value, prefix=''):
    """Generate a unique ID based on the value."""
    if pd.isna(value) or value is None:
        return None
    hash_obj = hashlib.md5(str(value).encode())
    return f"{prefix}{hash_obj.hexdigest()[:8]}"


def parse_merchant(val):
    """Parse merchant dict-like string into name + URL."""
    if pd.isna(val):
        return None, None
    
    try:
        val_clean = str(val).replace("'", '"')
        d = json.loads(val_clean)
        return d.get("name"), d.get("url")
    except json.JSONDecodeError:
        try:
            d = ast.literal_eval(str(val))
            return d.get("name"), d.get("url")
        except Exception as e:
            logger.warning(f"Failed to parse merchant: {val} | Error: {e}")
            return None, None
    except Exception as e:
        logger.warning(f"Unexpected error parsing merchant: {val} | Error: {e}")
        return None, None


def extract_size(title):
    """Extract numeric size and unit from product title."""
    if not isinstance(title, str):
        return None, None
    
    pattern = r'(\d+(?:\.\d+)?)\s*(?:x\s*)?(\d+(?:\.\d+)?)?\s*(ml|g|kg|oz|l|pack|packs|pcs|tabs|bars)'
    match = re.search(pattern, title.lower())
    
    if match:
        try:
            if match.group(2):
                value = float(match.group(2))
            else:
                value = float(match.group(1))
            unit = match.group(3)
            return value, unit
        except (ValueError, IndexError):
            return None, None
    
    return None, None


def extract_brand(title):
    """Extract brand name from product title."""
    if not isinstance(title, str):
        return None
    
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in title_lower:
            return brand
    
    tokens = title.split()
    brand_tokens = []
    
    for token in tokens[:3]:
        if token and token[0].isupper():
            brand_tokens.append(token)
        else:
            break
    
    return " ".join(brand_tokens[:2]) if brand_tokens else None


def clean_product_name(title):
    """Remove size/unit indicators from product title."""
    if not isinstance(title, str):
        return None
    
    title = re.sub(
        r'\b\d+(?:\.\d+)?\s*(?:x\s*)?\d*\s*(ml|g|kg|oz|l|pack|packs|pcs|tabs|bars)\b',
        '', 
        title, 
        flags=re.IGNORECASE
    )
    
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'[-,|]\s*$', '', title).strip()
    
    return title if title else None


# === MAIN PROCESSING FUNCTION ===

def create_normalized_tables(input_file, output_dir="."):
    """
    Process raw data and create normalized CSV files matching the EER diagram.
    
    Creates 5 separate CSV files:
    - brand.csv
    - category.csv
    - price_source.csv
    - retailer.csv
    - product.csv
    - price_history.csv
    """
    logger.info(f"🚀 Starting normalized data processing for: {input_file}")
    
    # === 1. Load raw data ===
    try:
        df = pd.read_csv(input_file)
        logger.info(f"✅ Loaded {len(df)} rows from {input_file}")
    except Exception as e:
        logger.error(f"❌ Failed to load file: {e}")
        raise
    
    # === 2. Extract all required fields ===
    logger.info("🔄 Extracting data fields...")
    
    df["retailer_name_clean"], df["retailer_url"] = zip(*df["merchant"].apply(parse_merchant))
    df["size_value"], df["size_unit"] = zip(*df["title"].apply(extract_size))
    df["brand_name_clean"] = df["title"].apply(extract_brand)
    df["product_name_clean"] = df["title"].apply(clean_product_name)
    df["category_name_clean"] = df["search_query"].fillna("Unknown").str.title()
    
    # === 3. CREATE BRAND TABLE ===
    logger.info("📊 Creating Brand table...")
    brands = df[['brand_name_clean']].drop_duplicates().dropna()
    brands = brands.rename(columns={'brand_name_clean': 'brand_name'})
    brands['brand_id'] = brands['brand_name'].apply(lambda x: generate_id(x, 'BRD'))
    brands = brands[['brand_id', 'brand_name']]
    
    # === 4. CREATE CATEGORY TABLE ===
    logger.info("📊 Creating Category table...")
    categories = df[['category_name_clean']].drop_duplicates().dropna()
    categories = categories.rename(columns={'category_name_clean': 'category_name'})
    categories['category_id'] = categories['category_name'].apply(lambda x: generate_id(x, 'CAT'))
    categories = categories[['category_id', 'category_name']]
    
    # === 5. CREATE PRICE_SOURCE TABLE ===
    logger.info("📊 Creating Price_Source table...")
    price_source = pd.DataFrame({
        'source_id': ['SRC00000001'],
        'source_name': ['Oxylabs Google Shopping'],
        'region': ['GB']
    })
    
    # === 6. CREATE RETAILER TABLE ===
    logger.info("📊 Creating Retailer table...")
    retailers = df[['retailer_name_clean']].drop_duplicates().dropna()
    retailers = retailers.rename(columns={'retailer_name_clean': 'retailer_name'})
    retailers['retailer_id'] = retailers['retailer_name'].apply(lambda x: generate_id(x, 'RET'))
    retailers['source_id'] = 'SRC00000001'
    retailers = retailers[['retailer_id', 'source_id', 'retailer_name']]
    
    # === 7. CREATE PRODUCT TABLE ===
    logger.info("📊 Creating Product table...")
    
    # Create lookup dictionaries for foreign keys
    brand_lookup = dict(zip(brands['brand_name'], brands['brand_id']))
    category_lookup = dict(zip(categories['category_name'], categories['category_id']))
    
    # Map foreign keys
    df['brand_id'] = df['brand_name_clean'].map(brand_lookup)
    df['category_id'] = df['category_name_clean'].map(category_lookup)
    
    # Create product table
    products = df[['product_name_clean', 'brand_id', 'category_id', 'size_value', 'size_unit']].copy()
    products = products.rename(columns={'product_name_clean': 'product_name'})
    
    # Replace NaN with None for proper NULL handling in CSV
    products['brand_id'] = products['brand_id'].where(pd.notna(products['brand_id']), None)
    products['size_value'] = products['size_value'].where(pd.notna(products['size_value']), None)
    products['size_unit'] = products['size_unit'].where(pd.notna(products['size_unit']), None)
    
    # Generate unique product_id based on product name + brand + category
    products['product_key'] = (
        products['product_name'].fillna('') + '_' + 
        products['brand_id'].fillna('') + '_' + 
        products['category_id'].fillna('')
    )
    products['product_id'] = products['product_key'].apply(lambda x: generate_id(x, 'PRD'))
    
    # Remove duplicates and drop temporary key
    products = products.drop_duplicates(subset=['product_id'])
    products = products[['product_id', 'product_name', 'brand_id', 'category_id', 'size_value', 'size_unit']]
    
    # === 8. CREATE PRICE_HISTORY TABLE ===
    logger.info("📊 Creating Price_History table...")
    
    # Create retailer lookup
    retailer_lookup = dict(zip(retailers['retailer_name'], retailers['retailer_id']))
    df['retailer_id'] = df['retailer_name_clean'].map(retailer_lookup)
    
    # Map product_id to main dataframe
    product_lookup = dict(zip(
        products['product_name'] + '_' + products['brand_id'].fillna('') + '_' + products['category_id'].fillna(''),
        products['product_id']
    ))
    df['product_key'] = (
        df['product_name_clean'].fillna('') + '_' + 
        df['brand_id'].fillna('') + '_' + 
        df['category_id'].fillna('')
    )
    df['product_id'] = df['product_key'].map(product_lookup)
     # Create price_history table
    price_history = df[['product_id', 'retailer_id', 'price', 'currency', 'timestamp', 'url', 'thumbnail']].copy()
    price_history = price_history.rename(columns={'timestamp': 'date_collected'})
    price_history['discount'] = np.nan

    # Generate price_id
    price_history['price_id'] = range(1, len(price_history) + 1)
    price_history['price_id'] = price_history['price_id'].apply(lambda x: f"PRC{x:08d}")

    # Remove rows with missing critical data
    price_history = price_history.dropna(subset=['product_id', 'retailer_id'])

    price_history = price_history[['price_id', 'product_id', 'retailer_id', 'price', 'discount', 'currency', 'date_collected', 'url', 'thumbnail']]
    
    # === 9. SAVE ALL TABLES ===
    logger.info("💾 Saving normalized tables...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    tables = {
        'brand': brands,
        'category': categories,
        'price_source': price_source,
        'retailer': retailers,
        'product': products,
        'price_history': price_history
    }
    
    saved_files = []
    for table_name, table_df in tables.items():
        filename = f"{output_dir}/{table_name}_{timestamp}.csv"
        table_df.to_csv(filename, index=False)
        saved_files.append(filename)
        logger.info(f"   ✅ {table_name}.csv - {len(table_df)} rows")
    
    # === 10. GENERATE SUMMARY ===
    logger.info("=" * 60)
    logger.info("📊 DATA NORMALIZATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total input rows: {len(df)}")
    logger.info(f"\nOutput Tables:")
    logger.info(f"   - Brands: {len(brands)}")
    logger.info(f"   - Categories: {len(categories)}")
    logger.info(f"   - Price Sources: {len(price_source)}")
    logger.info(f"   - Retailers: {len(retailers)}")
    logger.info(f"   - Products: {len(products)}")
    logger.info(f"   - Price History: {len(price_history)}")
    logger.info("=" * 60)
    logger.info("🎉 Normalization complete!")
    
    return tables


# === SCRIPT EXECUTION ===

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "shopping_results_20251008_145450.csv"
    
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    try:
        tables = create_normalized_tables(input_file, output_dir)
        
        # Display samples
        print("\n📋 Sample data from each table:\n")
        for table_name, table_df in tables.items():
            print(f"\n{'='*60}")
            print(f"{table_name.upper()} TABLE (first 3 rows):")
            print(f"{'='*60}")
            print(table_df.head(3).to_string(index=False))
        
    except Exception as e:
        logger.error(f"💥 Script failed: {e}")
        sys.exit(1)