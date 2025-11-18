#!/usr/bin/env python3
"""
Post-Processing Matcher for Unmatched Products

This script takes the unmatched products from the enhanced matching engine
and performs additional matching to catch obvious duplicates and similar products
that were missed by the main engine.
"""

import os
import pandas as pd
import numpy as np
from rapidfuzz import fuzz
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("post_processor")

OUTPUT_DIR = "data/processed"

# More lenient thresholds for post-processing
MIN_SIMILARITY = 60
PERFECT_THRESHOLD = 95

def normalize_text(text: str) -> str:
    """Basic text normalization."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    import re
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def token_overlap(a: str, b: str) -> float:
    """Jaccard token overlap in [0, 100]."""
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens & b_tokens)
    union = len(a_tokens | b_tokens)
    return (inter / union) * 100.0

def find_matches_in_unmatched(unmatched_df: pd.DataFrame) -> pd.DataFrame:
    """Find matches within the unmatched products dataset."""
    matches = []
    
    # Group by category for efficiency
    for category, group in unmatched_df.groupby('category_name'):
        group = group.reset_index(drop=True)
        n = len(group)
        log.info(f"Processing {category}: {n} unmatched products")
        
        for i in range(n):
            row_i = group.iloc[i]
            for j in range(i + 1, n):
                row_j = group.iloc[j]
                
                # Skip if same product from same retailer (shouldn't happen in unmatched)
                if (row_i["product_id"] == row_j["product_id"] and 
                    row_i["retailer_clean"] == row_j["retailer_clean"]):
                    continue
                
                p1_clean = row_i["product_clean"]
                p2_clean = row_j["product_clean"]
                
                # Calculate similarity
                fuzz_score = fuzz.token_set_ratio(p1_clean, p2_clean)
                overlap_score = token_overlap(p1_clean, p2_clean)
                lexical_similarity = 0.6 * fuzz_score + 0.4 * overlap_score
                
                # Start with lexical similarity
                score = float(lexical_similarity)
                
                # Brand matching
                b1 = row_i["brand_clean"]
                b2 = row_j["brand_clean"]
                brand_similarity = 0.0
                
                if pd.notna(b1) and pd.notna(b2) and b1 and b2:
                    if b1 == b2:
                        brand_similarity = 100.0
                        score += 25.0  # Higher bonus for exact brand match
                    else:
                        brand_similarity = 0.0
                        score -= 15.0  # Less penalty than main engine
                else:
                    brand_similarity = 50.0
                
                # Size matching (if available)
                size_similarity = 50.0
                if (pd.notna(row_i["size_value"]) and pd.notna(row_j["size_value"]) and
                    pd.notna(row_i["size_unit"]) and pd.notna(row_j["size_unit"])):
                    try:
                        s1, s2 = float(row_i["size_value"]), float(row_j["size_value"])
                        u1, u2 = str(row_i["size_unit"]).lower(), str(row_j["size_unit"]).lower()
                        
                        if u1 == u2:
                            if s1 == s2:
                                size_similarity = 100.0
                                score += 15.0
                            elif abs(s1 - s2) / max(s1, s2) <= 0.1:  # 10% tolerance
                                size_similarity = 80.0
                                score += 10.0
                            else:
                                size_similarity = 30.0
                        else:
                            size_similarity = 10.0
                            score -= 5.0
                    except:
                        pass
                
                # Special cases for obvious matches
                # 1. Exact same product_id (different retailers)
                if row_i["product_id"] == row_j["product_id"]:
                    score = 100.0  # Force perfect match for identical products
                
                # 2. Very high lexical similarity (likely same product)
                elif lexical_similarity >= 95:
                    score = max(score, 95.0)
                
                # 3. Same brand + high similarity (likely variants)
                elif (pd.notna(b1) and pd.notna(b2) and b1 == b2 and 
                      lexical_similarity >= 70):
                    score += 10.0  # Extra boost for same brand
                
                # Clip score
                score = max(0.0, min(100.0, score))
                
                if score >= MIN_SIMILARITY:
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
                        "lexical_similarity": round(lexical_similarity, 2),
                        "brand_similarity": round(brand_similarity, 2),
                        "size_similarity": round(size_similarity, 2),
                        "match_source": "post_processing"
                    })
    
    if matches:
        return pd.DataFrame(matches)
    else:
        return pd.DataFrame()

def merge_with_existing_matches(new_matches_df: pd.DataFrame, existing_matches_file: str) -> pd.DataFrame:
    """Merge new matches with existing matches."""
    if new_matches_df.empty:
        log.warning("No new matches to merge")
        return pd.DataFrame()
    
    # Load existing matches
    existing_df = pd.read_csv(existing_matches_file)
    log.info(f"Loaded {len(existing_df)} existing matches")
    
    # Add match_source column to existing matches if not present
    if 'match_source' not in existing_df.columns:
        existing_df['match_source'] = 'main_engine'
    
    # Ensure columns are compatible
    common_columns = set(existing_df.columns) & set(new_matches_df.columns)
    existing_df = existing_df[list(common_columns)]
    new_matches_df = new_matches_df[list(common_columns)]
    
    # Combine
    combined_df = pd.concat([existing_df, new_matches_df], ignore_index=True)
    
    log.info(f"Combined: {len(existing_df)} existing + {len(new_matches_df)} new = {len(combined_df)} total matches")
    
    return combined_df

def find_latest_file(pattern: str) -> str:
    """Find the latest file matching a pattern."""
    import glob
    files = glob.glob(os.path.join(OUTPUT_DIR, pattern))
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    return max(files, key=os.path.getctime)

def main():
    log.info("Starting post-processing matcher for unmatched products")
    
    try:
        # Find latest unmatched products file
        unmatched_file = find_latest_file("unmatched_products_enhanced_*.csv")
        log.info(f"Using unmatched products file: {unmatched_file}")
        
        # Load unmatched products
        unmatched_df = pd.read_csv(unmatched_file)
        log.info(f"Loaded {len(unmatched_df)} unmatched products")
        
        # Find matches within unmatched products
        new_matches_df = find_matches_in_unmatched(unmatched_df)
        
        if new_matches_df.empty:
            log.info("No additional matches found in unmatched products")
            return
        
        log.info(f"Found {len(new_matches_df)} new matches in unmatched products")
        
        # Find latest enhanced matches file
        enhanced_matches_file = find_latest_file("matched_products_enhanced_*.csv")
        log.info(f"Using enhanced matches file: {enhanced_matches_file}")
        
        # Merge with existing matches
        combined_matches = merge_with_existing_matches(new_matches_df, enhanced_matches_file)
        
        # Save results
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save new matches separately
        new_matches_file = os.path.join(OUTPUT_DIR, f"post_processed_matches_{ts}.csv")
        new_matches_df.to_csv(new_matches_file, index=False)
        log.info(f"Saved new matches to: {new_matches_file}")
        
        # Save combined matches
        combined_file = os.path.join(OUTPUT_DIR, f"combined_matches_enhanced_{ts}.csv")
        combined_matches.to_csv(combined_file, index=False)
        log.info(f"Saved combined matches to: {combined_file}")
        
        # Update unmatched products (remove newly matched ones)
        newly_matched_ids = set(new_matches_df["product_1_id"]) | set(new_matches_df["product_2_id"])
        remaining_unmatched = unmatched_df[~unmatched_df["product_id"].isin(newly_matched_ids)]
        
        remaining_file = os.path.join(OUTPUT_DIR, f"remaining_unmatched_{ts}.csv")
        remaining_unmatched.to_csv(remaining_file, index=False)
        
        # Summary
        log.info("POST-PROCESSING SUMMARY:")
        log.info(f"  Original unmatched products: {len(unmatched_df)}")
        log.info(f"  New matches found: {len(new_matches_df)}")
        log.info(f"  Newly matched products: {len(newly_matched_ids)}")
        log.info(f"  Remaining unmatched: {len(remaining_unmatched)}")
        log.info(f"  Improvement: {len(newly_matched_ids) / len(unmatched_df) * 100:.1f}% reduction in unmatched")
        
        # Analyze match types
        perfect_matches = len(new_matches_df[new_matches_df["similarity"] >= PERFECT_THRESHOLD])
        log.info(f"  Perfect matches (≥{PERFECT_THRESHOLD}%): {perfect_matches}")
        
        # Show some examples
        log.info("\nSample new matches:")
        for _, row in new_matches_df.head(3).iterrows():
            log.info(f"  {row['similarity']:.1f}%: {row['product_1_name'][:50]}... vs {row['product_2_name'][:50]}...")
        
        log.info("Post-processing completed successfully!")
        
    except Exception as e:
        log.error(f"Post-processing failed: {e}")
        raise

if __name__ == "__main__":
    main()
