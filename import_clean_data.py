import pyodbc
import pandas as pd
from datetime import datetime
import numpy as np

print("=" * 60)
print("Importing Cleaned CSV Data")
print("=" * 60)

# Database connection settings
server = 'localhost,1433'
database = 'MyFirstDatabase'
username = 'sa'
password = 'MyPass123!'

conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes'

# Collection date
collection_date = datetime(2025, 10, 2, 0, 0, 0)

def safe_value(value):
    """Convert pandas NaN/None to proper None for SQL Server"""
    if pd.isna(value) or value is None:
        return None
    # Convert numpy bool to Python bool
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    # Convert numpy int to Python int
    if isinstance(value, (np.integer,)):
        return int(value)
    # Convert numpy float to Python float
    if isinstance(value, (np.floating,)):
        return float(value)
    return value

def get_retailer_id(cursor, domain):
    """Get retailer_id for a given domain"""
    cursor.execute("""
        SELECT retailer_id FROM pricing.retailers 
        WHERE domain = ?
    """, domain)
    result = cursor.fetchone()
    return result[0] if result else None

def insert_product(cursor, retailer_id, asin, title, brand, url):
    """Insert or get existing product"""
    # Check if product exists
    cursor.execute("""
        SELECT product_id FROM pricing.products 
        WHERE retailer_id = ? AND external_id = ?
    """, retailer_id, asin)
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Insert new product
    cursor.execute("""
        INSERT INTO pricing.products (retailer_id, external_id, brand, title, url)
        VALUES (?, ?, ?, ?, ?)
    """, retailer_id, asin, brand, title, url)
    
    cursor.execute("SELECT @@IDENTITY")
    return cursor.fetchone()[0]

def insert_snapshot(cursor, product_id, row, collection_date):
    """Insert price snapshot with safe value conversion"""
    cursor.execute("""
        INSERT INTO pricing.price_snapshots (
            product_id, collected_at_utc, currency, current_price, 
            list_price, coupon_value, coupon_type, best_seller,
            is_prime, is_sponsored, availability, shipping_info,
            rating, reviews_total, sales_volume, pos,
            size_value, size_unit, price_per_100, search_keyword, market_domain
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, 
        product_id,
        collection_date,
        safe_value(row.get('currency')),
        safe_value(row.get('price')),
        safe_value(row.get('price_strikethrough')),
        safe_value(row.get('coupon_discount')),
        safe_value(row.get('coupon_discount_type')),
        safe_value(row.get('best_seller')),
        safe_value(row.get('is_prime')),
        safe_value(row.get('is_sponsored')),
        safe_value(row.get('not_available')),
        safe_value(row.get('shipping_information')),
        safe_value(row.get('rating')),
        safe_value(row.get('reviews_count')),
        safe_value(row.get('sales_volume')),
        safe_value(row.get('pos')),
        safe_value(row.get('size_value')),
        safe_value(row.get('size_unit')),
        safe_value(row.get('price_per_100unit_final')),
        safe_value(row.get('search_keyword')),
        safe_value(row.get('amazon_domain'))
    )

def main():
    print("\n📁 Reading cleaned_beauty_data.csv...")
    df = pd.read_csv('cleaned_beauty_data.csv')
    print(f"   Found {len(df)} rows to import")
    
    print("\n🔌 Connecting to database...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print("   ✓ Connected")
    
    inserted_products = 0
    inserted_snapshots = 0
    errors = 0
    
    print("\n⚙️  Importing data...")
    
    for idx, row in df.iterrows():
        try:
            # Get retailer_id
            domain = safe_value(row.get('amazon_domain'))
            retailer_id = get_retailer_id(cursor, domain)
            
            if not retailer_id:
                print(f"   ⚠️  Row {idx}: No retailer found for domain '{domain}'")
                errors += 1
                continue
            
            # Insert/get product
            product_id = insert_product(
                cursor, 
                retailer_id, 
                safe_value(row.get('asin')),
                safe_value(row.get('title')), 
                safe_value(row.get('manufacturer')), 
                safe_value(row.get('url'))
            )
            
            inserted_products += 1
            
            # Insert snapshot
            insert_snapshot(cursor, product_id, row, collection_date)
            inserted_snapshots += 1
            
            # Progress update every 100 rows
            if (idx + 1) % 100 == 0:
                conn.commit()
                print(f"   ✓ Processed {idx + 1}/{len(df)} rows...")
        
        except Exception as e:
            error_msg = str(e)[:200]
            print(f"   ✗ Error on row {idx}: {error_msg}")
            errors += 1
            continue
    
    # Final commit
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ IMPORT COMPLETE!")
    print("=" * 60)
    print(f"Products inserted: {inserted_products}")
    print(f"Snapshots inserted: {inserted_snapshots}")
    print(f"Errors: {errors}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()