#!/usr/bin/env python3
"""
Debug version of enhanced matching engine to find why obvious matches are missed
"""

import os
import json
from datetime import datetime
import re
import logging

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from rapidfuzz import fuzz

# Database connection
DB_USER = "postgres"
DB_PASSWORD = "your_postgres_password"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "aue_warehouse"
SCHEMA = "aue"

def normalize_text(text: str) -> str:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def token_overlap(a: str, b: str) -> float:
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return (inter / union) * 100.0

def load_and_prepare_data():
    """Load and prepare data for matching"""
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(url)
    
    query = f"""
        SELECT
            p.product_id,
            p.product_name,
            p.brand_id,
            b.brand_name,
            p.category_id,
            c.category_name,
            p.size_value,
            p.size_unit,
            s.price,
            s.currency,
            s.date_collected,
            r.retailer_name
        FROM {SCHEMA}.product p
        LEFT JOIN {SCHEMA}.brand b
            ON p.brand_id = b.brand_id
        LEFT JOIN {SCHEMA}.category c
            ON p.category_id = c.category_id
        LEFT JOIN {SCHEMA}.stg_price_snapshot s
            ON p.product_id = s.product_id
        LEFT JOIN {SCHEMA}.retailer r
            ON s.retailer_id = r.retailer_id;
    """
    
    df = pd.read_sql(query, con=engine)
    print(f"Loaded {len(df)} rows from database")
    
    # Prepare normalized columns
    df = df.dropna(subset=["product_id", "product_name"]).copy()
    df["product_clean"] = df["product_name"].apply(normalize_text)
    df["brand_clean"] = df["brand_name"].apply(normalize_text)
    df["category_clean"] = df["category_name"].apply(normalize_text)
    df["retailer_clean"] = df["retailer_name"].apply(normalize_text)
    
    # Deduplication
    before_dedup = len(df)
    df = df.drop_duplicates(
        subset=[
            "product_id",
            "retailer_clean",
            "product_clean",
            "brand_clean",
            "category_clean",
            "size_value",
            "size_unit",
        ]
    ).reset_index(drop=True)
    after_dedup = len(df)
    
    print(f"After deduplication: {after_dedup} rows (removed {before_dedup - after_dedup})")
    
    return df

def debug_little_soap_matching(df):
    """Debug specifically the Little Soap Company case"""
    print("\n" + "="*60)
    print("DEBUGGING LITTLE SOAP COMPANY MATCHING")
    print("="*60)
    
    # Find Little Soap Company products
    little_soap = df[df['product_name'].str.contains('Little Soap Company Eco Warrior', case=False, na=False)]
    print(f"Found {len(little_soap)} Little Soap Company products:")
    
    for i, row in little_soap.iterrows():
        print(f"  {i}: ID={row['product_id']}, retailer='{row['retailer_clean']}', clean_name='{row['product_clean']}'")
    
    if len(little_soap) < 2:
        print("❌ Less than 2 products found - no matching possible!")
        return
    
    # Check if they're in the same category group
    categories = little_soap['category_clean'].unique()
    print(f"Categories: {categories}")
    
    # Test matching within category
    for category, group in little_soap.groupby('category_clean'):
        print(f"\nCategory '{category}': {len(group)} products")
        
        if len(group) < 2:
            continue
            
        group = group.reset_index(drop=True)
        
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                row_i = group.iloc[i]
                row_j = group.iloc[j]
                
                print(f"\n  Testing pair {i}-{j}:")
                print(f"    Product 1: {row_i['product_name']}")
                print(f"    Product 2: {row_j['product_name']}")
                
                # Check skip condition
                same_id = row_i["product_id"] == row_j["product_id"]
                same_retailer = row_i["retailer_clean"] == row_j["retailer_clean"]
                should_skip = same_id and same_retailer
                
                print(f"    Same ID: {same_id}, Same retailer: {same_retailer}, Skip: {should_skip}")
                
                if should_skip:
                    print("    ❌ SKIPPED")
                    continue
                
                # Calculate similarity
                p1_clean = row_i["product_clean"]
                p2_clean = row_j["product_clean"]
                
                fuzz_score = fuzz.token_set_ratio(p1_clean, p2_clean)
                overlap_score = token_overlap(p1_clean, p2_clean)
                lexical_score = 0.6 * fuzz_score + 0.4 * overlap_score
                
                # Brand match
                same_brand = row_i["brand_clean"] == row_j["brand_clean"]
                score = lexical_score
                if same_brand:
                    score += 20.0
                
                print(f"    Fuzz: {fuzz_score}, Overlap: {overlap_score}, Lexical: {lexical_score}")
                print(f"    Same brand: {same_brand}, Final score: {score}")
                
                if score >= 65:
                    print(f"    ✅ SHOULD MATCH (score {score})")
                else:
                    print(f"    ❌ Below threshold (score {score})")

def main():
    print("🐛 DEBUG: Enhanced Matching Engine")
    print("="*50)
    
    try:
        df = load_and_prepare_data()
        debug_little_soap_matching(df)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
