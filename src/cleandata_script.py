#!/usr/bin/env python3
"""
Clean & Normalize Raw Product Data
----------------------------------
This script performs advanced cleaning of scraped product data before
fuzzy matching and deduplication. It extracts brand, size, pack quantity,
and normalized product names, and computes derived metrics such as total size.
"""

import re
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
KNOWN_BRANDS = [
    'Garnier', 'Friendly Soap', 'Kitsch', 'Faith in Nature', 
    'Davines', 'Soaphoria', 'weDo', 'Biovene', 'Little Soap Company',
    'Eco Warrior', 'LOOKFANTASTIC', 'Justmylook', 'Anihana', 'Tree Hut',
    'The Earthling Co.', 'Ethique', 'Abhati Suisse'
]

UNIT_MAP = {
    "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "g": "g", "gram": "g", "grams": "g",
    "kg": "g", "oz": "oz", "ounce": "oz", "ounces": "oz",
    "l": "ml", "litre": "ml", "litres": "ml",
    "pcs": "pcs", "bars": "pcs", "tabs": "pcs", "pack": "pcs", "packs": "pcs"
}

# === CORE CLEANING FUNCTIONS ===

def extract_pack_and_size(title: str):
    """Extract pack quantity and size with unit from title text."""
    if not isinstance(title, str):
        return None, None, None

    title_l = title.lower()
    pack_qty, size_val, size_unit = None, None, None

    # --- Pack quantity patterns ---
    pack_patterns = [
        r'(\d+)\s*[-]?\s*pack',
        r'pack\s*of\s*(\d+)',
        r'bulk\s*x\s*(\d+)',
        r'\((?:x)?(\d+)[- ]?pack\)',
        r'(\d+)[xX]\s*(?:pcs|pieces|bars|items)?',
        r'(\d+)\s*pcs'
    ]
    for p in pack_patterns:
        m = re.search(p, title_l)
        if m:
            pack_qty = int(m.group(1))
            break

    # --- Size patterns ---
    size_patterns = [
        r'(\d+(?:\.\d+)?)\s*(ml|g|gram|grams|kg|oz|ounce|ounces|l|litre|litres)'
    ]
    for p in size_patterns:
        m = re.search(p, title_l)
        if m:
            size_val = float(m.group(1))
            size_unit = UNIT_MAP.get(m.group(2), m.group(2))
            break

    return pack_qty, size_val, size_unit


def normalize_total_size(row):
    """Compute total size in consistent units (ml or g)."""
    if pd.isna(row["size_value"]):
        return np.nan
    pack = row["pack_qty"] if not pd.isna(row["pack_qty"]) else 1
    total = pack * row["size_value"]
    return total


def extract_brand(title: str):
    """Extract brand using known brand list + capitalization logic."""
    if not isinstance(title, str):
        return None

    title_l = title.lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in title_l:
            return brand

    # fallback: take first capitalized tokens
    tokens = title.split()
    brand_tokens = [t for t in tokens[:3] if t and t[0].isupper()]
    return " ".join(brand_tokens) if brand_tokens else None


def clean_title_text(title: str):
    """Clean product title for matching."""
    if not isinstance(title, str):
        return None

    title = re.sub(
        r'\b\d+(?:\.\d+)?\s*(x\s*\d+)?\s*(ml|g|kg|oz|l|litre|pack|packs|pcs|bars|tabs)\b',
        '', title, flags=re.IGNORECASE)
    title = re.sub(r'[^a-zA-Z0-9\s]+', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip().lower()
    return title


# === MAIN CLEANING FUNCTION ===

def clean_raw_data(input_file, output_file="cleaned_products.csv"):
    """Main cleaning pipeline."""
    logger.info(f"🔹 Cleaning file: {input_file}")
    df = pd.read_csv(input_file)
    logger.info(f"Loaded {len(df)} rows")

    # --- Extract brand, size, pack ---
    df["brand_clean"] = df["title"].apply(extract_brand)
    df["pack_qty"], df["size_value"], df["size_unit"] = zip(*df["title"].apply(extract_pack_and_size))
    df["total_size"] = df.apply(normalize_total_size, axis=1)

    # --- Clean product text ---
    df["product_clean"] = df["title"].apply(clean_title_text)
    df["category_clean"] = df["search_query"].fillna("Unknown").str.lower()

    # --- Fill NaNs and strip whitespace ---
    df = df.fillna({"brand_clean": "none", "category_clean": "unknown"})
    df["product_clean"] = df["product_clean"].str.strip()

    # --- Export ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Ensure output goes to data/processed/intermediate directory
    os.makedirs("data/processed/intermediate", exist_ok=True)
    filename = os.path.basename(output_file.replace('.csv', ''))
    output_path = f"data/processed/intermediate/{filename}_{timestamp}.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"✅ Cleaned data saved to: {output_path}")

    # --- Summary stats ---
    logger.info("📊 Cleaning Summary:")
    logger.info(f"Brands extracted: {df['brand_clean'].nunique()}")
    logger.info(f"Size detected in: {df['size_value'].notna().mean()*100:.1f}% rows")
    logger.info(f"Pack detected in: {df['pack_qty'].notna().mean()*100:.1f}% rows")

    return df


# === EXECUTION ===
if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "raw_products.csv"
    clean_raw_data(input_file)
