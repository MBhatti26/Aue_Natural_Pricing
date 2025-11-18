#!/usr/bin/env python3
"""
Enhanced Product Matching Engine for Auê Natural with Vector Embeddings

- Extends the original matching engine with semantic similarity using sentence embeddings
- Combines lexical matching (RapidFuzz + Jaccard) with semantic similarity (Sentence-BERT)
- Uses a hybrid scoring approach for better product matching
- Maintains all original features: category-aware, brand-weighted, size-aware matching
"""

import os
import json
from datetime import datetime
import re
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

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

# Matching thresholds - slightly adjusted for hybrid scoring
MIN_SIMILARITY = 65          # Lowered slightly due to semantic component
PERFECT_THRESHOLD = 88       # Adjusted for hybrid scoring

# Size compatibility tolerance (fraction difference allowed)
SIZE_TOLERANCE = 0.20        # 20%

# Embedding weights for hybrid scoring
LEXICAL_WEIGHT = 0.6         # Weight for lexical similarity (RapidFuzz + Jaccard)
SEMANTIC_WEIGHT = 0.4        # Weight for semantic similarity (embeddings)

# Embedding model configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, good quality model
EMBEDDING_CACHE_FILE = "data/processed/embeddings_cache.pkl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("enhanced_matching_engine")


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


# ==============================
# EMBEDDING UTILITIES
# ==============================

class EmbeddingManager:
    """Manages sentence embeddings with caching for efficient computation."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL, cache_file: str = EMBEDDING_CACHE_FILE):
        self.model_name = model_name
        self.cache_file = cache_file
        self.model = None
        self.cache = {}
        
        # Load cache if it exists
        self._load_cache()
    
    def _load_cache(self):
        """Load embeddings cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                log.info(f"Loaded embeddings cache with {len(self.cache)} entries.")
            except Exception as e:
                log.warning(f"Failed to load embeddings cache: {e}")
                self.cache = {}
        else:
            log.info("No existing embeddings cache found. Starting fresh.")
    
    def _save_cache(self):
        """Save embeddings cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            log.info(f"Saved embeddings cache with {len(self.cache)} entries.")
        except Exception as e:
            log.error(f"Failed to save embeddings cache: {e}")
    
    def _get_model(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            log.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            log.info("Model loaded successfully.")
        return self.model
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text, using cache if available."""
        if not text or text.strip() == "":
            return np.zeros(384)  # MiniLM-L6-v2 embedding dimension
        
        # Use normalized text as cache key
        cache_key = normalize_text(text)
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Compute new embedding
        model = self._get_model()
        embedding = model.encode([text])[0]
        
        # Cache the result
        self.cache[cache_key] = embedding
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a batch of texts efficiently."""
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if not text or text.strip() == "":
                embeddings.append(np.zeros(384))
                continue
                
            cache_key = normalize_text(text)
            if cache_key in self.cache:
                embeddings.append(self.cache[cache_key])
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Compute embeddings for uncached texts
        if uncached_texts:
            log.info(f"Computing embeddings for {len(uncached_texts)} new texts...")
            model = self._get_model()
            new_embeddings = model.encode(uncached_texts)
            
            # Update cache and embeddings list
            for idx, embedding in zip(uncached_indices, new_embeddings):
                cache_key = normalize_text(texts[idx])
                self.cache[cache_key] = embedding
                embeddings[idx] = embedding
        
        return np.array(embeddings)
    
    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts using embeddings."""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        
        # Reshape for sklearn cosine_similarity
        similarity = cosine_similarity([emb1], [emb2])[0][0]
        
        # Convert to 0-100 scale like other similarity scores
        return float(similarity * 100)
    
    def cleanup(self):
        """Save cache before cleanup."""
        self._save_cache()


# ==============================
# HELPERS (Enhanced)
# ==============================

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


def compute_hybrid_name_similarity(name1: str, name2: str, embedding_manager: EmbeddingManager) -> Tuple[float, float, float]:
    """
    Compute hybrid name similarity combining lexical and semantic approaches.
    
    Returns:
        (hybrid_score, lexical_score, semantic_score)
    """
    # Lexical similarity (existing approach)
    fuzz_score = fuzz.token_set_ratio(name1, name2)
    overlap_score = token_overlap(name1, name2)
    lexical_score = 0.6 * fuzz_score + 0.4 * overlap_score
    
    # Semantic similarity using embeddings
    semantic_score = embedding_manager.compute_semantic_similarity(name1, name2)
    
    # Hybrid combination
    hybrid_score = LEXICAL_WEIGHT * lexical_score + SEMANTIC_WEIGHT * semantic_score
    
    return hybrid_score, lexical_score, semantic_score


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


def prepare_matching_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare normalized columns for matching.
    We keep one row per (product_id, retailer_name, product_clean) combination.
    """
    df = df.dropna(subset=["product_id", "product_name"]).copy()

    # Normalize for matching
    df["product_clean"] = df["product_name"].apply(normalize_text)
    df["brand_clean"] = df["brand_name"].apply(normalize_text)
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


def compute_matches_enhanced(df: pd.DataFrame, embedding_manager: EmbeddingManager) -> pd.DataFrame:
    """
    Perform enhanced category-aware, brand-weighted, size-aware fuzzy matching with semantic similarity.
    Returns a DataFrame of product pairs with similarity scores and components.
    """
    matches = []

    # Group by category so we only compare like-for-like
    # (e.g., all shampoo bars with shampoo bars)
    for category, group in df.groupby("category_clean"):
        group = group.reset_index(drop=True)
        n = len(group)
        log.info("Matching category '%s' with %d rows.", category or "unknown", n)

        # Pre-compute subcategories for this group
        group["subcat"] = group["product_clean"].apply(detect_subcategory)

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

                # --- Enhanced name similarity (hybrid lexical + semantic) ---
                hybrid_similarity, lexical_similarity, semantic_similarity = compute_hybrid_name_similarity(
                    p1_clean, p2_clean, embedding_manager
                )

                # Start from hybrid name similarity as base score
                score = float(hybrid_similarity)

                # --- Brand similarity & scoring ---
                b1 = row_i["brand_clean"]
                b2 = row_j["brand_clean"]

                if b1 and b2:
                    if b1 == b2:
                        brand_similarity = 100.0
                        score += 20.0
                    else:
                        brand_similarity = 0.0
                        score -= 25.0
                else:
                    # Missing brand; neutral-ish
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

                # Clip final score to [0, 100]
                score = max(0.0, min(100.0, score))

                if score < MIN_SIMILARITY:
                    continue

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
                    "hybrid_name_similarity": round(hybrid_similarity, 2),
                    "lexical_similarity": round(lexical_similarity, 2),
                    "semantic_similarity": round(semantic_similarity, 2),
                    "brand_similarity": round(brand_similarity, 2),
                    "size_similarity": round(size_similarity, 2),
                })

    if not matches:
        log.warning("No matches found above similarity threshold %d.", MIN_SIMILARITY)
        return pd.DataFrame()

    matches_df = pd.DataFrame(matches)
    log.info("Computed %d matching pairs above similarity %d.", len(matches_df), MIN_SIMILARITY)
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
    um["reason_unmatched"] = f"No match >= {MIN_SIMILARITY} (enhanced)"
    return um


def save_outputs_enhanced(df_raw: pd.DataFrame, matches_df: pd.DataFrame):
    """Save enhanced matching outputs with additional semantic similarity columns."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if matches_df.empty:
        unmatched_df = compute_unmatched(df_raw, matches_df)
        unmatched_path = os.path.join(OUTPUT_DIR, f"unmatched_products_{ts}.csv")
        unmatched_df.to_csv(unmatched_path, index=False)
        log.info("Saved unmatched products to %s (no matches found).", unmatched_path)

        summary = {
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "engine_version": "enhanced_with_embeddings_v1",
                "total_processing_time": "N/A"
            },
            "dataset_overview": {
                "total_products": int(df_raw["product_id"].nunique()),
                "matched_products": 0,
                "unmatched_products": int(len(unmatched_df)),
                "coverage_percentage": 0.0
            },
            "matching_results": {
                "total_pairs": 0,
                "perfect_matches": 0,
                "similar_matches": 0
            },
            "technical_details": {
                "embedding_model": EMBEDDING_MODEL,
                "lexical_weight": LEXICAL_WEIGHT,
                "semantic_weight": SEMANTIC_WEIGHT,
                "similarity_thresholds": {
                    "minimum": MIN_SIMILARITY,
                    "perfect": PERFECT_THRESHOLD
                }
            }
        }
        summary_path = os.path.join(OUTPUT_DIR, f"processing_summary_{ts}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        log.info("Saved matching summary to %s.", summary_path)
        return

    # All matched pairs (main output)
    matched_path = os.path.join(OUTPUT_DIR, f"processed_matches_{ts}.csv")
    matches_df.to_csv(matched_path, index=False)

    # Unmatched products  
    unmatched_df = compute_unmatched(df_raw, matches_df)
    unmatched_path = os.path.join(OUTPUT_DIR, f"unmatched_products_{ts}.csv")
    unmatched_df.to_csv(unmatched_path, index=False)

    # Calculate stats for summary (but don't save redundant files)
    perfect_df = matches_df[matches_df["similarity"] >= PERFECT_THRESHOLD].copy()
    similar_df = matches_df[(matches_df["similarity"] >= MIN_SIMILARITY) &
                            (matches_df["similarity"] < PERFECT_THRESHOLD)].copy()

    # Enhanced summary JSON with semantic similarity statistics
    matched_ids = set(matches_df["product_1_id"]) | set(matches_df["product_2_id"])
    total_products = int(df_raw["product_id"].nunique())
    matched_products = int(len(matched_ids))
    unmatched_products = int(len(unmatched_df))
    coverage = (matched_products / total_products) * 100 if total_products > 0 else 0.0

    # Compute semantic similarity statistics
    semantic_stats = {
        "avg_semantic_similarity": float(matches_df["semantic_similarity"].mean()),
        "avg_lexical_similarity": float(matches_df["lexical_similarity"].mean()),
        "avg_hybrid_similarity": float(matches_df["hybrid_name_similarity"].mean()),
        "semantic_high_matches": int(len(matches_df[matches_df["semantic_similarity"] >= 80])),
        "lexical_high_matches": int(len(matches_df[matches_df["lexical_similarity"] >= 80])),
    }

    summary = {
        "processing_metadata": {
            "timestamp": datetime.now().isoformat(),
            "engine_version": "enhanced_with_embeddings_v1",
            "total_processing_time": "N/A"
        },
        "dataset_overview": {
            "total_products": total_products,
            "matched_products": matched_products,
            "unmatched_products": unmatched_products,
            "coverage_percentage": round(coverage, 1)
        },
        "matching_results": {
            "total_pairs": int(len(matches_df)),
            "perfect_matches": int(len(perfect_df)),
            "similar_matches": int(len(similar_df))
        },
        "technical_details": {
            "embedding_model": EMBEDDING_MODEL,
            "lexical_weight": LEXICAL_WEIGHT,
            "semantic_weight": SEMANTIC_WEIGHT,
            "similarity_thresholds": {
                "minimum": MIN_SIMILARITY,
                "perfect": PERFECT_THRESHOLD
            }
        },
        "semantic_analysis": semantic_stats
    }
    summary_path = os.path.join(OUTPUT_DIR, f"processing_summary_{ts}.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    log.info("Saved enhanced matching outputs:")
    log.info("  Processed matches -> %s", matched_path)
    log.info("  Unmatched products -> %s", unmatched_path)
    log.info("  Processing summary -> %s", summary_path)


def main():
    log.info("Starting enhanced product matching engine with vector embeddings.")
    
    # Initialize embedding manager
    embedding_manager = EmbeddingManager()
    
    try:
        engine = get_engine()

        log.info("Loading product data from PostgreSQL...")
        df_raw = load_product_frame(engine)
        
        log.info("Preparing frame for matching...")
        df_for_matching = prepare_matching_frame(df_raw)

        log.info("Computing enhanced matches with semantic similarity...")
        matches_df = compute_matches_enhanced(df_for_matching, embedding_manager)
        
        log.info("Saving enhanced outputs...")
        save_outputs_enhanced(df_for_matching, matches_df)

        log.info("Enhanced product matching engine completed successfully.")
        
    except Exception as e:
        log.error(f"Error in enhanced matching engine: {e}")
        raise
    finally:
        # Always save embeddings cache before exit
        embedding_manager.cleanup()


if __name__ == "__main__":
    main()
