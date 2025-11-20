#!/usr/bin/env python3
"""
Merge Post-Processed Matches with Main Matches

This script properly merges the post-processed matches into the main matched products CSV
and removes the newly matched products from the unmatched CSV.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("merge_matches")

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # File paths
    main_matches_file = "data/processed/processed_matches_20251119_170950.csv"
    post_matches_file = "data/processed/post_processed_matches_20251119_181222.csv"
    unmatched_file = "data/processed/unmatched_products_20251119_170950.csv"
    
    log.info("Loading existing matched products...")
    main_matches = pd.read_csv(main_matches_file)
    log.info(f"Loaded {len(main_matches)} existing matches")
    
    log.info("Loading post-processed matches...")
    post_matches = pd.read_csv(post_matches_file)
    log.info(f"Loaded {len(post_matches)} post-processed matches")
    
    log.info("Loading unmatched products...")
    unmatched = pd.read_csv(unmatched_file)
    log.info(f"Loaded {len(unmatched)} unmatched products")
    
    # Standardize post-processed matches to match main format
    log.info("Standardizing post-processed matches format...")
    
    # Add missing columns with default values
    post_matches['hybrid_name_similarity'] = np.nan
    post_matches['semantic_similarity'] = np.nan
    post_matches['processing_date'] = '2025-11-19'
    post_matches['engine_version'] = 'enhanced_with_embeddings_v1'
    post_matches['confidence_tier'] = 'LOW'  # Post-processing typically finds lower confidence matches
    post_matches['match_rank'] = 1  # Will be recalculated later
    
    # Reorder columns to match main format
    target_columns = main_matches.columns.tolist()
    
    # Ensure all target columns exist in post_matches
    for col in target_columns:
        if col not in post_matches.columns:
            post_matches[col] = np.nan
    
    post_matches = post_matches[target_columns]
    
    # Merge the matches
    log.info("Merging matches...")
    combined_matches = pd.concat([main_matches, post_matches], ignore_index=True)
    log.info(f"Combined total: {len(combined_matches)} matches")
    
    # Get list of newly matched product IDs
    newly_matched_ids = set()
    for _, row in post_matches.iterrows():
        newly_matched_ids.add(row['product_1_id'])
        newly_matched_ids.add(row['product_2_id'])
    
    log.info(f"Found {len(newly_matched_ids)} newly matched product IDs")
    
    # Remove newly matched products from unmatched list
    log.info("Removing newly matched products from unmatched list...")
    original_unmatched_count = len(unmatched)
    updated_unmatched = unmatched[~unmatched['product_id'].isin(newly_matched_ids)]
    new_unmatched_count = len(updated_unmatched)
    removed_count = original_unmatched_count - new_unmatched_count
    
    log.info(f"Removed {removed_count} products from unmatched list")
    log.info(f"Remaining unmatched: {new_unmatched_count}")
    
    # Save updated files
    updated_matches_file = f"data/processed/updated_matches_{timestamp}.csv"
    updated_unmatched_file = f"data/processed/updated_unmatched_{timestamp}.csv"
    
    log.info(f"Saving updated matches to {updated_matches_file}...")
    combined_matches.to_csv(updated_matches_file, index=False)
    
    log.info(f"Saving updated unmatched to {updated_unmatched_file}...")
    updated_unmatched.to_csv(updated_unmatched_file, index=False)
    
    # Calculate new statistics
    total_products = 888  # From original dataset
    matched_products = total_products - new_unmatched_count
    coverage_percentage = (matched_products / total_products) * 100
    
    # Create updated summary
    summary = {
        "processing_metadata": {
            "timestamp": datetime.now().isoformat(),
            "engine_version": "enhanced_with_embeddings_v1_plus_postprocessing",
            "total_processing_time": "N/A"
        },
        "dataset_overview": {
            "total_products": total_products,
            "matched_products": matched_products,
            "unmatched_products": new_unmatched_count,
            "coverage_percentage": round(coverage_percentage, 1)
        },
        "matching_results": {
            "total_match_pairs": len(combined_matches),
            "main_engine_pairs": len(main_matches),
            "post_processing_pairs": len(post_matches)
        },
        "improvement_summary": {
            "original_unmatched": original_unmatched_count,
            "newly_matched_products": removed_count,
            "remaining_unmatched": new_unmatched_count,
            "coverage_improvement": f"{removed_count} products recovered ({round((removed_count/original_unmatched_count)*100, 1)}% reduction)"
        }
    }
    
    summary_file = f"data/processed/updated_processing_summary_{timestamp}.json"
    log.info(f"Saving updated summary to {summary_file}...")
    
    import json
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print final summary
    log.info("=== FINAL UPDATED STATISTICS ===")
    log.info(f"Total Products: {total_products}")
    log.info(f"Matched Products: {matched_products} ({coverage_percentage:.1f}% coverage)")
    log.info(f"Unmatched Products: {new_unmatched_count}")
    log.info(f"Total Match Pairs: {len(combined_matches)}")
    log.info(f"Post-Processing Recovered: {removed_count} products")
    log.info("=== FILES CREATED ===")
    log.info(f"Updated Matches: {updated_matches_file}")
    log.info(f"Updated Unmatched: {updated_unmatched_file}")
    log.info(f"Updated Summary: {summary_file}")
    
    return {
        'matches_file': updated_matches_file,
        'unmatched_file': updated_unmatched_file,
        'summary_file': summary_file,
        'stats': summary
    }

if __name__ == "__main__":
    main()
