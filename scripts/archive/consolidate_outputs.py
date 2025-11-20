#!/usr/bin/env python3
"""
Consolidated Output Generator for Enhanced Matching Engine

Creates a single, BI-friendly output file instead of multiple redundant CSVs.
Includes confidence tiers, match rankings, and all necessary metadata.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("consolidator")

OUTPUT_DIR = "data/processed"

def add_confidence_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Add confidence tier classification to matches."""
    def classify_confidence(similarity):
        if similarity >= 88:
            return "HIGH"
        elif similarity >= 70:
            return "MEDIUM"
        elif similarity >= 65:
            return "LOW"
        else:
            return "VERY_LOW"
    
    df['confidence_tier'] = df['similarity'].apply(classify_confidence)
    return df

def add_match_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Add match ranking (1 = best match for each product_1_id)."""
    df['match_rank'] = df.groupby('product_1_id')['similarity'].rank(method='dense', ascending=False).astype(int)
    return df

def add_metadata_columns(df: pd.DataFrame, match_source: str = "main_engine") -> pd.DataFrame:
    """Add metadata columns for better tracking."""
    df['match_source'] = match_source
    df['processing_date'] = datetime.now().strftime("%Y-%m-%d")
    df['engine_version'] = "enhanced_with_embeddings_v1"
    return df

def create_consolidated_output(enhanced_matches_file: str, post_processed_file: str = None) -> tuple:
    """Create a single consolidated output file from all match sources."""
    
    # Load main matches
    log.info(f"Loading enhanced matches from: {enhanced_matches_file}")
    main_matches = pd.read_csv(enhanced_matches_file)
    main_matches = add_metadata_columns(main_matches, "main_engine")
    
    # Load post-processed matches if available
    all_matches = [main_matches]
    
    if post_processed_file and os.path.exists(post_processed_file):
        log.info(f"Loading post-processed matches from: {post_processed_file}")
        post_matches = pd.read_csv(post_processed_file)
        post_matches = add_metadata_columns(post_matches, "post_processing")
        all_matches.append(post_matches)
    
    # Combine all matches
    consolidated_df = pd.concat(all_matches, ignore_index=True)
    
    # Add enhancements
    consolidated_df = add_confidence_tiers(consolidated_df)
    consolidated_df = add_match_rankings(consolidated_df)
    
    # Sort by product_1_id and match_rank for easy reading
    consolidated_df = consolidated_df.sort_values(['product_1_id', 'match_rank']).reset_index(drop=True)
    
    log.info(f"Consolidated {len(consolidated_df)} total matches from {len(all_matches)} sources")
    
    return consolidated_df

def generate_summary_stats(consolidated_df: pd.DataFrame, unmatched_df: pd.DataFrame) -> dict:
    """Generate comprehensive summary statistics."""
    
    total_products = len(set(consolidated_df['product_1_id']) | set(consolidated_df['product_2_id']) | set(unmatched_df['product_id']))
    matched_products = len(set(consolidated_df['product_1_id']) | set(consolidated_df['product_2_id']))
    
    summary = {
        "processing_metadata": {
            "timestamp": datetime.now().isoformat(),
            "engine_version": "enhanced_with_embeddings_v1",
            "total_processing_time": "N/A"
        },
        "dataset_overview": {
            "total_products": int(total_products),
            "matched_products": int(matched_products),
            "unmatched_products": len(unmatched_df),
            "coverage_percentage": round((matched_products / total_products) * 100, 1)
        },
        "matching_results": {
            "total_match_pairs": len(consolidated_df),
            "main_engine_pairs": len(consolidated_df[consolidated_df['match_source'] == 'main_engine']),
            "post_processing_pairs": len(consolidated_df[consolidated_df['match_source'] == 'post_processing'])
        },
        "confidence_breakdown": {
            tier: len(consolidated_df[consolidated_df['confidence_tier'] == tier])
            for tier in ["HIGH", "MEDIUM", "LOW", "VERY_LOW"]
        },
        "quality_metrics": {
            "avg_similarity": float(consolidated_df['similarity'].mean()),
            "median_similarity": float(consolidated_df['similarity'].median()),
            "avg_semantic_similarity": float(consolidated_df['semantic_similarity'].mean()) if 'semantic_similarity' in consolidated_df.columns else None,
            "avg_lexical_similarity": float(consolidated_df['lexical_similarity'].mean()) if 'lexical_similarity' in consolidated_df.columns else None
        },
        "business_impact": {
            "products_available_for_price_comparison": int(matched_products),
            "price_comparison_pairs": len(consolidated_df),
            "cross_retailer_matches": len(consolidated_df[consolidated_df['retailer_1'] != consolidated_df['retailer_2']])
        }
    }
    
    return summary

def find_latest_file(pattern: str) -> str:
    """Find the latest file matching a pattern."""
    import glob
    files = glob.glob(os.path.join(OUTPUT_DIR, pattern))
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    return max(files, key=os.path.getctime)

def main():
    log.info("Starting consolidated output generation")
    
    try:
        # Find latest files
        enhanced_file = find_latest_file("processed_matches_*.csv")
        unmatched_file = find_latest_file("unmatched_products_*.csv") 
        
        # Try to find post-processed file (may not exist)
        post_processed_file = None
        try:
            post_processed_file = find_latest_file("post_processed_matches_*.csv")
        except FileNotFoundError:
            log.info("No post-processed matches found, using main engine results only")
        
        # Load unmatched products
        unmatched_df = pd.read_csv(unmatched_file)
        log.info(f"Loaded {len(unmatched_df)} unmatched products")
        
        # Create consolidated output
        consolidated_df = create_consolidated_output(enhanced_file, post_processed_file)
        
        # Generate timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save consolidated matches
        consolidated_file = os.path.join(OUTPUT_DIR, f"processed_matches_{ts}.csv")
        consolidated_df.to_csv(consolidated_file, index=False)
        log.info(f"Saved consolidated matches to: {consolidated_file}")
        
        # Generate and save summary
        summary = generate_summary_stats(consolidated_df, unmatched_df)
        summary_file = os.path.join(OUTPUT_DIR, f"processing_summary_{ts}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        log.info(f"Saved processing summary to: {summary_file}")
        
        # Copy unmatched products with timestamp for consistency
        final_unmatched_file = os.path.join(OUTPUT_DIR, f"unmatched_products_{ts}.csv")
        unmatched_df.to_csv(final_unmatched_file, index=False)
        
        # Print summary
        log.info("\n" + "="*60)
        log.info("CONSOLIDATED OUTPUT SUMMARY")
        log.info("="*60)
        log.info(f"📊 Dataset: {summary['dataset_overview']['total_products']} products")
        log.info(f"✅ Matched: {summary['dataset_overview']['matched_products']} products ({summary['dataset_overview']['coverage_percentage']}%)")
        log.info(f"❌ Unmatched: {summary['dataset_overview']['unmatched_products']} products")
        log.info(f"🔗 Total Pairs: {summary['matching_results']['total_match_pairs']}")
        log.info("")
        log.info("📈 Confidence Breakdown:")
        for tier, count in summary['confidence_breakdown'].items():
            log.info(f"   {tier}: {count} pairs")
        log.info("")
        log.info("📁 Output Files:")
        log.info(f"   Main: {consolidated_file}")
        log.info(f"   Unmatched: {final_unmatched_file}")
        log.info(f"   Summary: {summary_file}")
        log.info("="*60)
        
        return consolidated_file, final_unmatched_file, summary_file
        
    except Exception as e:
        log.error(f"Consolidation failed: {e}")
        raise

if __name__ == "__main__":
    main()
