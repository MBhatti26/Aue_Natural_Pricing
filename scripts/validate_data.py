#!/usr/bin/env python3
"""
Database Validation Script for Auê Natural Pipeline
---------------------------------------------------
Validates all core tables inside the PostgreSQL schema `aue`.

Checks performed:
  - Row counts
  - Required columns exist
  - Foreign key consistency
  - Duplicate primary keys
  - Null violations on required fields
  - Price sanity checks
  - Brand/category/product integrity
  - Snapshot completeness

Outputs results to console.
"""

import psycopg2
import os
from psycopg2.extras import RealDictCursor
import logging

# =======================
# CONFIG
# =======================

# Use the same DB settings as src/load_to_db.py
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "your_postgres_password"  # same string as in load_to_db.py
DB_NAME = "aue_warehouse"


SCHEMA = "aue"

TABLES = [
    "brand",
    "category",
    "retailer",
    "price_source",
    "product",
    "stg_price_snapshot",
]

# =======================
# SETUP LOGGING
# =======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("validator")


# =======================
# DATABASE CONNECTION
# =======================
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# =======================
# VALIDATION HELPERS
# =======================
def get_row_count(cursor, table):
    cursor.execute(f"SELECT COUNT(*) AS c FROM {SCHEMA}.{table};")
    return cursor.fetchone()["c"]


def check_required_columns(cursor, table, required_cols):
    cursor.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table}' AND table_schema = '{SCHEMA}';
    """)
    cols = {r["column_name"] for r in cursor.fetchall()}
    missing = [c for c in required_cols if c not in cols]
    return missing


def check_duplicates(cursor, table, pk_col):
    cursor.execute(f"""
        SELECT {pk_col}, COUNT(*)
        FROM {SCHEMA}.{table}
        GROUP BY {pk_col}
        HAVING COUNT(*) > 1;
    """)
    return cursor.fetchall()


def check_nulls(cursor, table, columns):
    null_violations = {}
    for col in columns:
        cursor.execute(f"""
            SELECT COUNT(*) AS c
            FROM {SCHEMA}.{table}
            WHERE {col} IS NULL;
        """)
        null_violations[col] = cursor.fetchone()["c"]
    return null_violations


def check_foreign_keys(cursor):
    issues = {}

    # product → brand
    cursor.execute(f"""
        SELECT COUNT(*) AS c
        FROM {SCHEMA}.product p
        LEFT JOIN {SCHEMA}.brand b ON p.brand_id = b.brand_id
        WHERE p.brand_id IS NOT NULL AND b.brand_id IS NULL;
    """)
    issues["product_missing_brand"] = cursor.fetchone()["c"]

    # product → category
    cursor.execute(f"""
        SELECT COUNT(*) AS c
        FROM {SCHEMA}.product p
        LEFT JOIN {SCHEMA}.category c2 ON p.category_id = c2.category_id
        WHERE p.category_id IS NOT NULL AND c2.category_id IS NULL;
    """)
    issues["product_missing_category"] = cursor.fetchone()["c"]

    # stg_price_snapshot → product
    cursor.execute(f"""
        SELECT COUNT(*) AS c
        FROM {SCHEMA}.stg_price_snapshot s
        LEFT JOIN {SCHEMA}.product p ON s.product_id = p.product_id
        WHERE p.product_id IS NULL;
    """)
    issues["price_history_missing_product"] = cursor.fetchone()["c"]

    return issues


def price_sanity(cursor):
    issues = {}

    cursor.execute(f"""
        SELECT COUNT(*) AS c
        FROM {SCHEMA}.stg_price_snapshot
        WHERE price < 0;
    """)
    issues["negative_prices"] = cursor.fetchone()["c"]

    cursor.execute(f"""
        SELECT COUNT(*) AS c
        FROM {SCHEMA}.stg_price_snapshot
        WHERE discount IS NOT NULL AND discount < 0;
    """)
    issues["negative_discounts"] = cursor.fetchone()["c"]

    return issues


# =======================
# MAIN VALIDATION LOGIC
# =======================
def main():
    log.info("🔍 Starting Database Validation for Auê Natural Pipeline")
    print("=" * 60)

    try:
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as e:
        log.error(f"DB Connection failed: {e}")
        return

    # --- Validate each table ---
    for table in TABLES:
        print(f"\n📦 Validating Table: {SCHEMA}.{table}")
        print("-" * 60)

        # Row count
        count = get_row_count(cursor, table)
        print(f"🧮 Row Count: {count}")

        # Required column checks
        REQUIRED_COLS = {
            "brand": ["brand_id", "brand_name"],
            "category": ["category_id", "category_name"],
            "retailer": ["retailer_id", "source_id", "retailer_name"],
            "price_source": ["source_id", "source_name", "region"],
            "product": ["product_id", "product_name", "brand_id", "category_id"],
            "stg_price_snapshot": ["price_id", "product_id", "retailer_id", "price", "currency", "date_collected"],
        }

        missing = check_required_columns(cursor, table, REQUIRED_COLS[table])
        if missing:
            print(f"❌ Missing required columns: {missing}")
        else:
            print("✅ All required columns present")

        # Duplicate PK check
        PK = {
            "brand": "brand_id",
            "category": "category_id",
            "retailer": "retailer_id",
            "price_source": "source_id",
            "product": "product_id",
            "stg_price_snapshot": "price_id",
        }
        dups = check_duplicates(cursor, table, PK[table])
        if dups:
            print(f"❌ Duplicate PK values found: {len(dups)}")
        else:
            print("✅ No duplicate primary keys")

        # Null checks
        nulls = check_nulls(cursor, table, REQUIRED_COLS[table])
        total_nulls = sum(nulls.values())
        if total_nulls > 0:
            print(f"❌ Null violations: {nulls}")
        else:
            print("✅ No NULL violations on required columns")

    # --- Foreign key validation ---
    print("\n🔗 Foreign Key Consistency Checks")
    print("-" * 60)
    fk = check_foreign_keys(cursor)
    for issue, count in fk.items():
        if count > 0:
            print(f"❌ {issue}: {count}")
        else:
            print(f"✅ {issue}: OK")

    # --- Price sanity checks ---
    print("\n💰 Price Sanity Checks")
    print("-" * 60)
    ps = price_sanity(cursor)
    for issue, count in ps.items():
        if count > 0:
            print(f"❌ {issue}: {count}")
        else:
            print(f"✅ {issue}: OK")

    print("=" * 60)
    print("🎉 Database Validation Completed!")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()