#!/usr/bin/env python3
"""
Product Matching Engine for Auê Natural

- Reads normalized product + price data from PostgreSQL (schema: aue)
- Performs category-aware, brand-weighted, size-aware fuzzy matching
- Penalises generic titles (e.g. "Shampoo Bar", "Conditioner Bars") to avoid them
  acting as match magnets
- Uses blended similarity:
    * RapidFuzz token_set_ratio
    * Token overlap (Jaccard)
    * Brand match / mismatch
    * Size compatibility
    * Simple ingredient/function subcategory (e.g. Vitamin C, hyaluronic, curls)
- Outputs:
    * matched_products_clean_<timestamp>.csv
    * perfect_matches_<timestamp>.csv
    * similar_matches_<timestamp>.csv
    * unmatched_products_<timestamp>.csv
    * best_match_summary_<timestamp>.csv
    * matching_summary_<timestamp>.json
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
from sentence_transformers import SentenceTransformer, util

# ==============================
# CONFIG – POSTGRES CONNECTION
# ==============================

DB_USER = "postgres"
DB_PASSWORD = "your_postgres_password"   # <-- set this to the same value used in load_to_db.py
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "aue_warehouse"
SCHEMA = "aue"

OUTPUT_DIR = "data/processed"

# Matching thresholds
MIN_SIMILARITY = 70          # below this = no match
PERFECT_THRESHOLD = 90       # >= this = perfect match

# Size and price compatibility tolerance (fraction difference allowed)
SIZE_TOLERANCE = 0.30        # 30%
PRICE_TOLERANCE = 0.30       # 30%

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("matching_engine")


# ==============================
# DOMAIN CONSTANTS
# ==============================

# Titles that are too generic to be trusted as strong matches
GENERIC_TITLES = {
    "shampoo bar",
    "shampoo bars",
    "conditioner bar",
    "conditioner bars",
    "hair shampoo bar",
    "shampoo soap bars",
    "body butter",
    "body butters",
    "face serum",
    "serum",
    "brightening serum",
    "whipped body butter",
    "body butter moisturiser",
}

# Simple subcategory keywords (very light domain intelligence)
SUBCATEGORY_KEYWORDS = {
    "vitc": ["vitamin c", "vit c", "ascorbic"],
    "niacinamide": ["niacinamide", "vitamin b3", "vit b3"],
    "hyaluronic": ["hyaluronic", "ha ", " hyal ", "hyaluronic acid"],
    "retinol": ["retinol", "retinoid"],
    "anti_dandruff": ["anti dandruff", "anti-dandruff", "dandruff"],
    "curl": ["curly", "curl", "coily", "wavy"],
    "shea": ["shea butter", "shea"],
    "vanilla": ["vanilla"],
    "mango": ["mango"],
}

# Add brand normalization dictionary (example, expand as needed)
BRAND_MAP = {
    "coconut": "Generic",
    "shea butter": "Generic",
    "body butter": "Generic",
    "friendly fragrance": "Generic",
    "shea sea": "Generic",
    # Add more mappings as needed
}

# Ingredient keywords (expand as needed)
INGREDIENT_KEYWORDS = [
    "matrixyl", "niacinamide", "hyaluronic", "retinol", "ascorbic", "vitamin c", "vitamin b3", "shea", "vanilla", "mango"
]


# ==============================
# HELPERS
# ==============================

# Load embedding model once
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')


def get_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)


def normalize_text(text: str) -> str:
    """Basic text normalization: lowercase, strip, remove punctuation, collapse spaces."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def token_overlap(a: str, b: str) -> float:
    """
    Jaccard token overlap in [0, 100].
    Works well for retail titles where order is noisy.
    """
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return (inter / union) * 100.0


def is_generic_title(clean_name: str) -> bool:
    """
    Decide if a product name is too generic to be a strong match target.
    We only treat it as generic if the whole cleaned name matches one
    of the known generic titles.
    """
    if not clean_name:
        return False
    return clean_name in GENERIC_TITLES


def detect_subcategory(clean_name: str) -> str | None:
    """
    Very simple ingredient/function subcategory detection based on keywords.
    Returns a short code like 'vitc', 'hyaluronic', etc., or None.
    """
    if not clean_name:
        return None
    for code, keywords in SUBCATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in clean_name:
                return code
    return None


def size_similarity_and_effect(s1, u1, s2, u2):
    """
    Compute a coarse size similarity score and the effect on the final match score.

    Returns:
        size_sim (0/50/100),
        size_effect (float): adjustment applied to similarity
    """
    if s1 is None or s2 is None or u1 is None or u2 is None:
        # Unknown size; neutral but keep some "medium" similarity to show it's not a mismatch
        return 50.0, 0.0

    try:
        s1 = float(s1)
        s2 = float(s2)
    except ValueError:
        return 50.0, 0.0

    if str(u1).lower() != str(u2).lower():
        # Different units entirely
        return 0.0, -10.0

    bigger = max(s1, s2)
    smaller = min(s1, s2)
    if bigger == 0:
        return 50.0, 0.0

    diff_frac = (bigger - smaller) / bigger

    if diff_frac <= 0.05:
        # Essentially exact
        return 100.0, 20.0
    elif diff_frac <= SIZE_TOLERANCE:
        # Within tolerance range
        return 50.0, 10.0
    else:
        # Significantly different size
        return 0.0, -10.0


def load_product_frame(engine):
    """
    Load product + price + brand + category + retailer data from PostgreSQL.
    """
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
            s.date_key,
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
    log.info("Loaded %d product-price-retailer rows from PostgreSQL.", len(df))
    return df


def clean_brand(brand: str) -> str:
    brand = normalize_text(brand)
    return BRAND_MAP.get(brand, brand)


def prepare_matching_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare normalized columns for matching.
    We keep one row per (product_id, retailer_name, product_clean) combination.
    """
    df = df.dropna(subset=["product_id", "product_name"]).copy()

    # Normalize for matching
    df["product_clean"] = df["product_name"].apply(normalize_text)
    df["brand_clean"] = df["brand_name"].apply(clean_brand)
    df["category_clean"] = df["category_name"].apply(normalize_text)
    df["retailer_clean"] = df["retailer_name"].apply(normalize_text)

    # Deduplicate exact duplicates on relevant fields
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

    log.info("Prepared %d unique product-retailer rows for matching.", len(df))
    return df


def is_marketplace(retailer: str) -> bool:
    """Return True if retailer is a known marketplace or high-variance reseller."""
    retailer = normalize_text(retailer)
    return any(x in retailer for x in ["ebay", "amazon", "fruugo", "onbuy", "aliexpress", "etsy"])


def extract_ingredients(text: str) -> set:
    """Extract key ingredients from product name/description."""
    text = normalize_text(text)
    found = set()
    for kw in INGREDIENT_KEYWORDS:
        if kw in text:
            found.add(kw)
    return found


def semantic_similarity(a: str, b: str) -> float:
    """Compute cosine similarity between sentence embeddings."""
    emb_a = EMBEDDING_MODEL.encode(a, convert_to_tensor=True)
    emb_b = EMBEDDING_MODEL.encode(b, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(emb_a, emb_b).item()) * 100


def fuzzy_brand_match(b1, b2):
    """Fuzzy match for brand names."""
    if not b1 or not b2:
        return False
    score = fuzz.token_set_ratio(b1, b2)
    return score > 80


def fuzzy_ingredient_match(ing1, ing2):
    """Fuzzy match for ingredient sets."""
    if not ing1 or not ing2:
        return False
    return bool(set(ing1) & set(ing2))


def compute_matches(df: pd.DataFrame) -> pd.DataFrame:
    """
    Perform category-aware, brand-weighted, size-aware fuzzy matching.
    Returns a DataFrame of product pairs with similarity scores and components.
    """
    matches = []
    # Group by category so we only compare like-for-like
    for category, group in df.groupby("category_clean"):
        group = group.reset_index(drop=True)
        n = len(group)
        log.info("Matching category '%s' with %d rows.", category or "unknown", n)
        group["subcat"] = group["product_clean"].apply(detect_subcategory)
        group["ingredients"] = group["product_clean"].apply(extract_ingredients)
        for i in range(n):
            row_i = group.iloc[i]
            for j in range(i + 1, n):
                row_j = group.iloc[j]
                # Skip identical products from the same retailer (but allow same product from different retailers)
                if (row_i["product_id"] == row_j["product_id"] and 
                    row_i["retailer_clean"] == row_j["retailer_clean"]):
                    continue
                p1_clean = row_i["product_clean"]
                p2_clean = row_j["product_clean"]
                # Skip if one is generic and the other is not
                gen_i = is_generic_title(p1_clean)
                gen_j = is_generic_title(p2_clean)
                if gen_i != gen_j:
                    continue
                # Ingredient-level check (fuzzy)
                if not row_i["ingredients"] or not row_j["ingredients"]:
                    log.debug(f"Rejected: missing ingredients for {row_i['product_id']} or {row_j['product_id']}")
                    continue
                if not fuzzy_ingredient_match(row_i["ingredients"], row_j["ingredients"]):
                    log.debug(f"Rejected: ingredient mismatch {row_i['product_id']} vs {row_j['product_id']}")
                    continue
                # --- Name similarity (blended) ---
                fuzz_score = fuzz.token_set_ratio(row_i["product_clean"], row_j["product_clean"])
                overlap_score = token_overlap(row_i["product_clean"], row_j["product_clean"])
                sem_score = semantic_similarity(row_i["product_clean"], row_j["product_clean"])
                name_similarity = 0.4 * fuzz_score + 0.2 * overlap_score + 0.4 * sem_score
                score = float(name_similarity)
                # --- Brand similarity & scoring (fuzzy) ---
                b1 = row_i["brand_clean"]
                b2 = row_j["brand_clean"]
                if b1 and b2:
                    if fuzzy_brand_match(b1, b2):
                        brand_similarity = 100.0
                        score += 20.0
                    else:
                        brand_similarity = 0.0
                        score -= 25.0
                else:
                    brand_similarity = 50.0
                # --- Size similarity & scoring ---
                size_similarity, size_effect = size_similarity_and_effect(
                    row_i["size_value"], row_i["size_unit"],
                    row_j["size_value"], row_j["size_unit"]
                )
                score += size_effect
                # --- Subcategory similarity & scoring ---
                sub_i = row_i["subcat"]
                sub_j = row_j["subcat"]
                if sub_i and sub_j:
                    if sub_i == sub_j:
                        score += 10.0
                    else:
                        score -= 15.0
                # Flexible size filter: only allow matches within 30% and same unit
                try:
                    s1 = float(row_i["size_value"])
                    s2 = float(row_j["size_value"])
                    u1 = str(row_i["size_unit"]).lower()
                    u2 = str(row_j["size_unit"]).lower()
                except:
                    s1 = s2 = None
                    u1 = u2 = None
                if s1 and s2 and u1 == u2:
                    diff_frac = abs(s1 - s2) / max(s1, s2)
                    if diff_frac > SIZE_TOLERANCE:
                        log.debug(f"Rejected: size mismatch {row_i['product_id']} vs {row_j['product_id']}")
                        continue
                # Price normalization (per unit)
                price_1 = row_i["price"]
                price_2 = row_j["price"]
                if s1 and price_1:
                    try:
                        price_1_per_unit = float(price_1) / s1
                    except:
                        price_1_per_unit = None
                else:
                    price_1_per_unit = None
                if s2 and price_2:
                    try:
                        price_2_per_unit = float(price_2) / s2
                    except:
                        price_2_per_unit = None
                else:
                    price_2_per_unit = None
                # Flexible price filter: only allow matches within 30% per-unit price
                if price_1_per_unit and price_2_per_unit:
                    price_diff_frac = abs(price_1_per_unit - price_2_per_unit) / max(price_1_per_unit, price_2_per_unit)
                    if price_diff_frac > PRICE_TOLERANCE:
                        log.debug(f"Rejected: price mismatch {row_i['product_id']} vs {row_j['product_id']}")
                        continue
                # Clip final score to [0, 100]
                score = max(0.0, min(100.0, score))
                if score < MIN_SIMILARITY:
                    continue
                # Flag borderline matches for manual review
                borderline = False
                if (sem_score > 80 and (size_similarity < 50 or price_1_per_unit is None or price_2_per_unit is None)):
                    borderline = True
                matches.append({
                    "product_1_id": row_i["product_id"],
                    "product_2_id": row_j["product_id"],
                    "product_1_name": row_i["product_name"],
                    "product_2_name": row_j["product_name"],
                    "brand_1": row_i["brand_name"],
                    "brand_2": row_j["brand_name"],
                    "category": row_i["category_name"],
                    "size_value_1": row_i["size_value"],
                    "size_unit_1": row_i["size_unit"],
                    "size_value_2": row_j["size_value"],
                    "size_unit_2": row_j["size_unit"],
                    "price_1": row_i["price"],
                    "price_2": row_j["price"],
                    "currency_1": row_i["currency"],
                    "currency_2": row_j["currency"],
                    "retailer_1": row_i["retailer_name"],
                    "retailer_2": row_j["retailer_name"],
                    "similarity": round(score, 1),
                    "name_similarity": round(name_similarity, 2),
                    "brand_similarity": round(brand_similarity, 2),
                    "size_similarity": round(size_similarity, 2),
                    "price_1_per_unit": price_1_per_unit,
                    "price_2_per_unit": price_2_per_unit,
                    "borderline": borderline,
                })
    if not matches:
        log.warning("No matches found above similarity threshold %d.", MIN_SIMILARITY)
        return pd.DataFrame()
    matches_df = pd.DataFrame(matches)
    # Only keep best match per product_1_id
    best_idx = matches_df.groupby("product_1_id")["similarity"].idxmax()
    matches_df = matches_df.loc[best_idx].copy().reset_index(drop=True)
    log.info("Computed %d best matching pairs above similarity %d.", len(matches_df), MIN_SIMILARITY)
    return matches_df


def compute_unmatched(df_products: pd.DataFrame, matches_df: pd.DataFrame) -> pd.DataFrame:
    """Identify products with no match above threshold."""
    all_ids = set(df_products["product_id"].unique())
    if matches_df.empty:
        unmatched_ids = all_ids
    else:
        matched_ids = set(matches_df["product_1_id"]) | set(matches_df["product_2_id"])
        unmatched_ids = all_ids - matched_ids

    um = df_products[df_products["product_id"].isin(unmatched_ids)].copy()
    um["reason_unmatched"] = f"No match >= {MIN_SIMILARITY}"
    return um


def save_outputs(df_raw: pd.DataFrame, matches_df: pd.DataFrame):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Save main matches as FINAL_MATCHES.csv
    matched_path = os.path.join(OUTPUT_DIR, "FINAL_MATCHES.csv")
    matches_df.to_csv(matched_path, index=False)
    # Save unmatched as FINAL_UNMATCHED.csv
    unmatched_df = compute_unmatched(df_raw, matches_df)
    unmatched_path = os.path.join(OUTPUT_DIR, "FINAL_UNMATCHED.csv")
    unmatched_df.to_csv(unmatched_path, index=False)
    # Save summary as FINAL_SUMMARY.json
    matched_ids = set(matches_df["product_1_id"]) | set(matches_df["product_2_id"])
    total_products = int(df_raw["product_id"].nunique())
    matched_products = int(len(matched_ids))
    unmatched_products = int(len(unmatched_df))
    coverage = (matched_products / total_products) * 100 if total_products > 0 else 0.0
    summary = {
        "timestamp": ts,
        "total_products": total_products,
        "matched_pairs": int(len(matches_df)),
        "matched_products": matched_products,
        "unmatched_products": unmatched_products,
        "coverage_pct": round(coverage, 1)
    }
    summary_path = os.path.join(OUTPUT_DIR, "FINAL_SUMMARY.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Saved FINAL_MATCHES.csv, FINAL_UNMATCHED.csv, FINAL_SUMMARY.json.")


def main():
    log.info("Starting product matching engine.")
    engine = get_engine()
    log.info("Loading product data from PostgreSQL...")
    df_raw = load_product_frame(engine)
    log.info("Preparing frame for matching...")
    df_for_matching = prepare_matching_frame(df_raw)
    log.info("Computing matches...")
    matches_df = compute_matches(df_for_matching)
    log.info("Saving outputs...")
    save_outputs(df_for_matching, matches_df)
    log.info("Product matching engine completed.")


if __name__ == "__main__":
    main()
