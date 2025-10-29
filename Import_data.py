import pyodbc
import pandas as pd
from datetime import datetime
import re

print("Script started!")

# Database connection settings
server = 'localhost,1433'
database = 'MyFirstDatabase'
username = 'sa'
password = 'MyPass123!'

# Create connection string
conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes'

# Collection date
collection_date = datetime(2025, 10, 2, 0, 0, 0)

def clean_numeric(value):
    """Clean and convert numeric values, handling text and invalid formats"""
    if pd.isna(value) or value is None or value == '':
        return None
    
    # Convert to string for cleaning
    str_val = str(value).strip()
    
    # Return None for text values that can't be converted
    if any(char.isalpha() for char in str_val):
        return None
    
    # Remove common non-numeric characters except decimal point
    str_val = re.sub(r'[^\d.]', '', str_val)
    
    if str_val == '':
        return None
    
    try:
        # Convert to float and round to avoid precision errors
        num_val = float(str_val)
        return round(num_val, 4)
    except:
        return None

def clean_integer(value):
    """Clean and convert integer values"""
    if pd.isna(value) or value is None or value == '':
        return None
    
    str_val = str(value).strip()
    
    # Check if contains letters - if so, return None
    if any(char.isalpha() for char in str_val):
        return None
    
    # Extract just numbers
    str_val = re.sub(r'[^\d]', '', str_val)
    
    if str_val == '':
        return None
    
    try:
        return int(str_val)
    except:
        return None

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
    """Insert price snapshot with cleaned data"""
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
        row.get('currency'),
        clean_numeric(row.get('price')),
        clean_numeric(row.get('price_strikethrough')),
        clean_numeric(row.get('coupon_discount')),
        row.get('coupon_discount_type'),
        row.get('best_seller', False),
        row.get('is_prime', False),
        row.get('is_sponsored', False),
        row.get('not_available') if pd.notna(row.get('not_available')) else None,
        row.get('shipping_information'),
        clean_numeric(row.get('rating')),
        clean_integer(row.get('reviews_count')),
        clean_integer(row.get('sales_volume')),
        clean_integer(row.get('pos')),
        clean_numeric(row.get('size_value')),
        row.get('size_unit'),
        clean_numeric(row.get('price_per_100unit_final')),
        row.get('search_keyword'),
        row.get('amazon_domain')
    )

def process_csv(file_path, default_domain=None):
    """Process a CSV file and insert data"""
    print(f"\nProcessing {file_path}...")
    
    # Read CSV
    df = pd.read_csv(file_path)
    print(f"Found {len(df)} rows")
    
    # Connect to database
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    inserted_products = 0
    inserted_snapshots = 0
    skipped_rows = 0
    
    for idx, row in df.iterrows():
        try:
            # Determine domain
            domain = row.get('amazon_domain') if 'amazon_domain' in df.columns else default_domain
            
            if not domain:
                skipped_rows += 1
                continue
            
            # Get retailer_id
            retailer_id = get_retailer_id(cursor, domain)
            if not retailer_id:
                skipped_rows += 1
                continue
            
            # Skip if no ASIN or price
            asin = row.get('asin')
            price = clean_numeric(row.get('price'))
            
            if pd.isna(asin) or price is None:
                skipped_rows += 1
                continue
            
            # Extract brand/manufacturer
            brand = row.get('manufacturer') if pd.notna(row.get('manufacturer')) else None
            
            # Insert/get product
            product_id = insert_product(
                cursor, 
                retailer_id, 
                asin, 
                row.get('title'), 
                brand, 
                row.get('url')
            )
            
            if product_id:
                inserted_products += 1
            
            # Insert snapshot
            insert_snapshot(cursor, product_id, row, collection_date)
            inserted_snapshots += 1
            
            # Commit every 100 rows
            if idx % 100 == 0 and idx > 0:
                conn.commit()
                print(f"  ✓ Processed {idx} rows... ({inserted_snapshots} inserted, {skipped_rows} skipped)")
                
        except Exception as e:
            print(f"  ✗ Error on row {idx}: {str(e)[:100]}")
            skipped_rows += 1
            continue
    
    # Final commit
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✓ Completed! Inserted {inserted_products} products and {inserted_snapshots} snapshots")
    print(f"  Skipped {skipped_rows} rows due to errors or missing data\n")

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("Starting CSV import with data cleaning...")
    print("=" * 60)
    
    try:
        # Process UK data
        process_csv('amazon_uk_beauty_search.csv', default_domain='co.uk')
        
        # Process EU normalized data (has amazon_domain column)
        process_csv('amazon_eu_beauty_normalized.csv')
        
        print("=" * 60)
        print("✓ All data imported successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()