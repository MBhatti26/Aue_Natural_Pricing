#!/usr/bin/env python3
"""
Load Pipeline Output to Warehouse (FINAL VERSION)
Loads only the columns we decided to keep based on analytics needs
Handles date_key conversion from timestamp
"""

import psycopg2
import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

DB_CONFIG = {
    'dbname': 'aue_warehouse',
    'user': 'mahnoorbhatti',
    'host': 'localhost',
    'port': 5432
}

SCHEMA = 'aue'
PROCESSED_DIR = Path("data/processed")

# Columns to load - MATCHES create_clean_warehouse.sql EXACTLY
# These are ALL the columns from the CSV that exist in the warehouse schema
MATCHED_COLUMNS = [
    # Product 1
    'product_1_id', 'product_1_name', 'brand_1',
    'size_value_1', 'size_unit_1', 
    'price_1', 'currency_1', 'retailer_1',
    # Product 2
    'product_2_id', 'product_2_name', 'brand_2',
    'size_value_2', 'size_unit_2',
    'price_2', 'currency_2', 'retailer_2',
    # Common
    'category',
    # Similarity Scores (for match quality analysis)
    'similarity', 'hybrid_name_similarity', 'lexical_similarity',
    'semantic_similarity', 'brand_similarity', 'size_similarity',
    # Match Metadata (for time-series analysis)
    'match_source', 'processing_date', 'engine_version', 'confidence_tier', 'match_rank'
]

UNMATCHED_COLUMNS = [
    # Identification
    'product_id', 'product_name',
    'category_name', 'retailer_name',
    # Attributes
    'size_value', 'size_unit',
    'price', 'currency',
    # Cleaned fields
    'product_clean',
    # Metadata
    'reason_unmatched'
]

def get_db_connection():
    """Create PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        log.info(f"✅ Connected to database: {DB_CONFIG['dbname']}")
        return conn
    except Exception as e:
        log.error(f"❌ Connection failed: {e}")
        raise

def load_matched_products(conn):
    """Load matched products from processed_matches.csv"""
    log.info("\n📥 Loading matched_products...")
    
    csv_file = PROCESSED_DIR / "processed_matches.csv"
    if not csv_file.exists():
        log.warning(f"  ⚠️  File not found: {csv_file}")
        return 0
    
    df = pd.read_csv(csv_file)
    log.info(f"  📊 Read {len(df)} records")
    
    # Select only the essential columns we decided to keep
    df = df[MATCHED_COLUMNS].copy()
    
    cursor = conn.cursor()
    
    # Truncate table
    cursor.execute(f"TRUNCATE TABLE {SCHEMA}.matched_products RESTART IDENTITY CASCADE")
    log.info("  🗑️  Truncated table")
    
    # Insert records (only essential columns)
    columns = MATCHED_COLUMNS
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    insert_sql = f'INSERT INTO {SCHEMA}.matched_products ({columns_str}) VALUES ({placeholders})'
    
    records = df.values.tolist()
    cursor.executemany(insert_sql, records)
    conn.commit()
    
    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.matched_products")
    count = cursor.fetchone()[0]
    log.info(f"  ✅ Loaded {count:,} matched products")
    
    cursor.close()
    return count

def load_unmatched_products(conn):
    """Load unmatched products from unmatched_products.csv"""
    log.info("\n📥 Loading unmatched_products...")
    
    csv_file = PROCESSED_DIR / "unmatched_products.csv"
    if not csv_file.exists():
        log.warning(f"  ⚠️  File not found: {csv_file}")
        return 0
    
    df = pd.read_csv(csv_file)
    log.info(f"  📊 Read {len(df)} records")
    
    # Select only the essential columns we decided to keep
    df = df[UNMATCHED_COLUMNS].copy()
    
    cursor = conn.cursor()
    
    # Truncate table
    cursor.execute(f"TRUNCATE TABLE {SCHEMA}.unmatched_products RESTART IDENTITY CASCADE")
    log.info("  🗑️  Truncated table")
    
    # Insert records (only essential columns)
    columns = UNMATCHED_COLUMNS
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    insert_sql = f'INSERT INTO {SCHEMA}.unmatched_products ({columns_str}) VALUES ({placeholders})'
    
    records = df.values.tolist()
    cursor.executemany(insert_sql, records)
    conn.commit()
    
    # Verify
    cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.unmatched_products")
    count = cursor.fetchone()[0]
    log.info(f"  ✅ Loaded {count:,} unmatched products")
    
    cursor.close()
    return count

def verify_load(conn):
    """Verify data was loaded correctly"""
    log.info("\n" + "=" * 70)
    log.info("📊 VERIFICATION")
    log.info("=" * 70)
    
    cursor = conn.cursor()
    
    # Table counts
    cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.matched_products")
    matched_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA}.unmatched_products")
    unmatched_count = cursor.fetchone()[0]
    
    total = matched_count + unmatched_count
    
    log.info(f"✅ Matched products:   {matched_count:,}")
    log.info(f"✅ Unmatched products: {unmatched_count:,}")
    log.info(f"📦 Total products:     {total:,}")
    
    # Category breakdown
    log.info("\n📋 Categories:")
    cursor.execute(f"""
        SELECT category, COUNT(*) 
        FROM {SCHEMA}.matched_products 
        GROUP BY category 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    for category, count in cursor.fetchall():
        log.info(f"  • {category}: {count:,}")
    
    # Sample price comparison
    log.info("\n💰 Sample Price Comparison:")
    cursor.execute(f"""
        SELECT product_1_name, retailer_1, price_1, retailer_2, price_2, similarity
        FROM {SCHEMA}.matched_products
        WHERE price_1 IS NOT NULL AND price_2 IS NOT NULL
        LIMIT 5
    """)
    for row in cursor.fetchall():
        log.info(f"  • {row[0][:40]}: {row[1]} R${row[2]:.2f} vs {row[3]} R${row[4]:.2f} (sim: {row[5]:.1f}%)")
    
    cursor.close()

def main():
    print("=" * 70)
    print("🏭 AUÊ NATURAL - LOAD PIPELINE OUTPUT TO WAREHOUSE")
    print("=" * 70)
    print("\nLoading pipeline output files:")
    print("  • data/processed/processed_matches.csv")
    print("  • data/processed/unmatched_products.csv")
    print()
    
    try:
        conn = get_db_connection()
        
        # Load both tables
        matched = load_matched_products(conn)
        unmatched = load_unmatched_products(conn)
        
        # Verify
        verify_load(conn)
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ WAREHOUSE LOAD COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Loaded {matched + unmatched:,} total products")
        print("\n🎯 Your warehouse is ready for queries!")
        print("\n💡 Try these queries:")
        print(f"   SELECT * FROM {SCHEMA}.price_comparison LIMIT 10;")
        print(f"   SELECT * FROM {SCHEMA}.best_matches_by_category;")
        print(f"   SELECT * FROM {SCHEMA}.retailer_coverage;")
        
        return 0
        
    except Exception as e:
        log.error(f"❌ Load failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
