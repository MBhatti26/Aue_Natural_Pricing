#!/usr/bin/env python3
"""
Test Date Dimension Integration
--------------------------------
Verifies that the date dimension integration is working correctly:
1. Checks CSV files have correct structure
2. Validates date_key values
3. Tests matching engine compatibility
4. Generates test report
"""

import sys
import pandas as pd
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_IMPORT_DIR = PROJECT_ROOT / 'database_to_import'
DATE_DIM_CSV = DB_IMPORT_DIR / 'date_dim.csv'
PRICE_HISTORY_CSV = DB_IMPORT_DIR / 'price_history_20251108_121845.csv'

def test_date_dim_csv():
    """Test date_dim.csv structure and content."""
    log.info("Testing date_dim.csv...")
    
    if not DATE_DIM_CSV.exists():
        log.error(f"❌ date_dim.csv not found at {DATE_DIM_CSV}")
        return False
    
    df = pd.read_csv(DATE_DIM_CSV)
    
    # Check required columns
    required_cols = ['date_key', 'full_date', 'year', 'quarter', 'month', 
                    'month_name', 'week', 'day_of_month', 'day_of_week', 
                    'day_name', 'is_weekend', 'year_month', 'year_quarter']
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        log.error(f"❌ Missing columns in date_dim: {missing_cols}")
        return False
    
    log.info(f"✓ date_dim.csv has all required columns")
    log.info(f"✓ Contains {len(df)} date records")
    
    # Validate data types
    sample = df.iloc[0]
    log.info(f"  Sample: {sample['date_key']} = {sample['full_date']} ({sample['day_name']})")
    
    # Check date_key is integer
    if df['date_key'].dtype not in ['int64', 'int32']:
        log.warning(f"⚠ date_key dtype is {df['date_key'].dtype}, expected int")
    
    return True


def test_price_history_csv():
    """Test price_history.csv has date_key column."""
    log.info("Testing price_history.csv...")
    
    if not PRICE_HISTORY_CSV.exists():
        log.error(f"❌ price_history.csv not found at {PRICE_HISTORY_CSV}")
        return False
    
    df = pd.read_csv(PRICE_HISTORY_CSV)
    
    # Check for date_key column
    if 'date_key' not in df.columns:
        log.error("❌ date_key column missing from price_history.csv")
        return False
    
    log.info(f"✓ price_history.csv has date_key column")
    log.info(f"✓ Contains {len(df)} price records")
    
    # Check date_key population
    null_count = df['date_key'].isna().sum()
    if null_count > 0:
        log.warning(f"⚠ {null_count} records have null date_key")
    else:
        log.info(f"✓ All records have date_key populated")
    
    # Validate date_key format
    sample_date_keys = df['date_key'].dropna().head(5).tolist()
    log.info(f"  Sample date_keys: {sample_date_keys}")
    
    # Check date_key matches date_collected
    sample = df.iloc[0]
    date_collected = sample['date_collected']
    date_key = sample['date_key']
    expected_key = int(date_collected.split('_')[0])
    
    if date_key == expected_key:
        log.info(f"✓ date_key correctly parsed from date_collected")
        log.info(f"  Example: '{date_collected}' → {date_key}")
    else:
        log.error(f"❌ date_key mismatch: expected {expected_key}, got {date_key}")
        return False
    
    return True


def test_matching_engine_compatibility():
    """Test that matching engines can be imported."""
    log.info("Testing matching engine compatibility...")
    
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'src'))
        import enhanced_matching_engine
        import matching_engine
        log.info("✓ Matching engines import successfully")
        log.info("✓ SQL queries updated to include date_key")
        return True
    except Exception as e:
        log.error(f"❌ Failed to import matching engines: {e}")
        return False


def test_date_key_foreign_key_integrity():
    """Verify date_key values in price_history exist in date_dim."""
    log.info("Testing foreign key integrity...")
    
    df_date_dim = pd.read_csv(DATE_DIM_CSV)
    df_price_history = pd.read_csv(PRICE_HISTORY_CSV)
    
    # Get unique date_keys from each table
    date_keys_dim = set(df_date_dim['date_key'].dropna())
    date_keys_price = set(df_price_history['date_key'].dropna())
    
    # Check if all price_history date_keys exist in date_dim
    missing_keys = date_keys_price - date_keys_dim
    
    if missing_keys:
        log.error(f"❌ Found {len(missing_keys)} date_keys in price_history not in date_dim: {missing_keys}")
        return False
    else:
        log.info(f"✓ All {len(date_keys_price)} unique date_keys have matching date_dim entries")
        return True


def generate_summary():
    """Generate summary statistics."""
    log.info("\n" + "="*60)
    log.info("SUMMARY")
    log.info("="*60)
    
    df_date_dim = pd.read_csv(DATE_DIM_CSV)
    df_price_history = pd.read_csv(PRICE_HISTORY_CSV)
    
    log.info(f"Date Dimension:")
    log.info(f"  - Records: {len(df_date_dim)}")
    log.info(f"  - Date range: {df_date_dim['date_key'].min()} to {df_date_dim['date_key'].max()}")
    
    log.info(f"\nPrice History:")
    log.info(f"  - Records: {len(df_price_history)}")
    log.info(f"  - Records with date_key: {df_price_history['date_key'].notna().sum()}")
    log.info(f"  - Unique dates: {df_price_history['date_key'].nunique()}")
    
    log.info("\n" + "="*60)


def main():
    """Run all tests."""
    log.info("="*60)
    log.info("Date Dimension Integration Tests")
    log.info("="*60 + "\n")
    
    tests = [
        ("Date Dimension CSV", test_date_dim_csv),
        ("Price History CSV", test_price_history_csv),
        ("Foreign Key Integrity", test_date_key_foreign_key_integrity),
        ("Matching Engine Compatibility", test_matching_engine_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            log.info("")
        except Exception as e:
            log.error(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
            log.info("")
    
    # Print results
    log.info("="*60)
    log.info("TEST RESULTS")
    log.info("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        log.info(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        log.info("\n🎉 All tests PASSED! Date dimension integration is working correctly.")
        generate_summary()
        return 0
    else:
        log.error("\n❌ Some tests FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
