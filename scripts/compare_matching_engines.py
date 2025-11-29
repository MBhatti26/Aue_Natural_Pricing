#!/usr/bin/env python3
"""
Matching Engine Comparison Script

Runs both the original matching engine and the enhanced version with embeddings,
then compares their performance and outputs detailed analysis.
"""

import os
import json
import subprocess
import sys
from datetime import datetime
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("matching_comparison")

OUTPUT_DIR = "data/processed"

def run_original_matching():
    """Run the original matching engine."""
    log.info("Running original matching engine...")
    try:
        result = subprocess.run([
            sys.executable, "src/matching_engine.py"
        ], capture_output=True, text=True, check=True)
        log.info("Original matching engine completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Original matching engine failed: {e}")
        log.error(f"Stdout: {e.stdout}")
        log.error(f"Stderr: {e.stderr}")
        return False

def run_enhanced_matching():
    """Run the enhanced matching engine with embeddings."""
    log.info("Running enhanced matching engine with embeddings...")
    try:
        result = subprocess.run([
            sys.executable, "src/enhanced_matching_engine.py"
        ], capture_output=True, text=True, check=True)
        log.info("Enhanced matching engine completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Enhanced matching engine failed: {e}")
        log.error(f"Stdout: {e.stdout}")
        log.error(f"Stderr: {e.stderr}")
        return False

def find_latest_files(pattern_prefix: str, pattern_suffix: str = ".json", exclude_pattern: str = None):
    """Find the latest files matching a pattern."""
    files = []
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith(pattern_prefix) and f.endswith(pattern_suffix):
            if exclude_pattern and exclude_pattern in f:
                continue
            files.append(f)
    
    if not files:
        return None
    
    # Sort by filename (timestamp embedded) and return the latest
    files.sort()
    return os.path.join(OUTPUT_DIR, files[-1])

def load_summary_files():
    """Load the latest summary files from both engines."""
    original_summary_file = find_latest_files("matching_summary_", ".json", exclude_pattern="enhanced")
    enhanced_summary_file = find_latest_files("matching_summary_enhanced_", ".json")
    
    original_summary = None
    enhanced_summary = None
    
    if original_summary_file:
        with open(original_summary_file, 'r') as f:
            original_summary = json.load(f)
        log.info(f"Loaded original summary: {original_summary_file}")
    
    if enhanced_summary_file:
        with open(enhanced_summary_file, 'r') as f:
            enhanced_summary = json.load(f)
        log.info(f"Loaded enhanced summary: {enhanced_summary_file}")
    
    return original_summary, enhanced_summary

def compare_results(original_summary, enhanced_summary):
    """Compare results between original and enhanced matching engines."""
    if not original_summary or not enhanced_summary:
        log.error("Cannot compare - missing summary files")
        return None
    
    comparison = {
        "comparison_timestamp": datetime.now().isoformat(),
        "original_engine": {
            "timestamp": original_summary.get("timestamp"),
            "total_products": original_summary.get("total_products"),
            "matched_pairs": original_summary.get("matched_pairs"),
            "matched_products": original_summary.get("matched_products"),
            "unmatched_products": original_summary.get("unmatched_products"),
            "coverage_pct": original_summary.get("coverage_pct"),
            "perfect_pairs": original_summary.get("perfect_pairs"),
            "similar_pairs": original_summary.get("similar_pairs")
        },
        "enhanced_engine": {
            "timestamp": enhanced_summary.get("timestamp"),
            "embedding_model": enhanced_summary.get("embedding_model"),
            "lexical_weight": enhanced_summary.get("lexical_weight"),
            "semantic_weight": enhanced_summary.get("semantic_weight"),
            "total_products": enhanced_summary.get("total_products"),
            "matched_pairs": enhanced_summary.get("matched_pairs"),
            "matched_products": enhanced_summary.get("matched_products"),
            "unmatched_products": enhanced_summary.get("unmatched_products"),
            "coverage_pct": enhanced_summary.get("coverage_pct"),
            "perfect_pairs": enhanced_summary.get("perfect_pairs"),
            "similar_pairs": enhanced_summary.get("similar_pairs"),
            "semantic_stats": enhanced_summary.get("semantic_stats", {})
        }
    }
    
    # Calculate improvements
    improvements = {}
    
    orig_coverage = original_summary.get("coverage_pct", 0)
    enh_coverage = enhanced_summary.get("coverage_pct", 0)
    improvements["coverage_improvement_pct"] = round(enh_coverage - orig_coverage, 1)
    
    orig_matched = original_summary.get("matched_products", 0)
    enh_matched = enhanced_summary.get("matched_products", 0)
    improvements["additional_matched_products"] = enh_matched - orig_matched
    
    orig_unmatched = original_summary.get("unmatched_products", 0)
    enh_unmatched = enhanced_summary.get("unmatched_products", 0)
    improvements["reduced_unmatched_products"] = orig_unmatched - enh_unmatched
    
    orig_pairs = original_summary.get("matched_pairs", 0)
    enh_pairs = enhanced_summary.get("matched_pairs", 0)
    improvements["additional_matched_pairs"] = enh_pairs - orig_pairs
    
    improvements["unmatched_reduction_pct"] = round(
        (improvements["reduced_unmatched_products"] / max(orig_unmatched, 1)) * 100, 1
    ) if orig_unmatched > 0 else 0
    
    comparison["improvements"] = improvements
    
    return comparison

def analyze_detailed_differences():
    """Analyze detailed differences in matching results."""
    # Find latest matched products files
    original_matches_file = find_latest_files("matched_products_clean_", ".csv", exclude_pattern="enhanced")
    enhanced_matches_file = find_latest_files("matched_products_enhanced_", ".csv")
    
    if not original_matches_file or not enhanced_matches_file:
        log.warning("Cannot perform detailed analysis - missing match files")
        return None
    
    try:
        original_matches = pd.read_csv(original_matches_file)
        enhanced_matches = pd.read_csv(enhanced_matches_file)
        
        log.info(f"Original matches: {len(original_matches)} pairs")
        log.info(f"Enhanced matches: {len(enhanced_matches)} pairs")
        
        # Analyze similarity score distributions
        analysis = {
            "original_similarity_stats": {
                "mean": float(original_matches["similarity"].mean()),
                "median": float(original_matches["similarity"].median()),
                "std": float(original_matches["similarity"].std()),
                "min": float(original_matches["similarity"].min()),
                "max": float(original_matches["similarity"].max())
            },
            "enhanced_similarity_stats": {
                "mean": float(enhanced_matches["similarity"].mean()),
                "median": float(enhanced_matches["similarity"].median()),
                "std": float(enhanced_matches["similarity"].std()),
                "min": float(enhanced_matches["similarity"].min()),
                "max": float(enhanced_matches["similarity"].max())
            }
        }
        
        if "semantic_similarity" in enhanced_matches.columns:
            analysis["semantic_similarity_stats"] = {
                "mean": float(enhanced_matches["semantic_similarity"].mean()),
                "median": float(enhanced_matches["semantic_similarity"].median()),
                "std": float(enhanced_matches["semantic_similarity"].std()),
                "min": float(enhanced_matches["semantic_similarity"].min()),
                "max": float(enhanced_matches["semantic_similarity"].max())
            }
        
        return analysis
        
    except Exception as e:
        log.error(f"Error in detailed analysis: {e}")
        return None

def save_comparison_report(comparison, detailed_analysis=None):
    """Save comprehensive comparison report."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(OUTPUT_DIR, f"matching_comparison_report_{ts}.json")
    
    full_report = {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "comparison_type": "original_vs_enhanced_with_embeddings"
        },
        "summary_comparison": comparison,
    }
    
    if detailed_analysis:
        full_report["detailed_analysis"] = detailed_analysis
    
    with open(report_file, 'w') as f:
        json.dump(full_report, f, indent=2)
    
    log.info(f"Saved comparison report to: {report_file}")
    return report_file

def print_comparison_summary(comparison):
    """Print a human-readable comparison summary."""
    print("\n" + "="*80)
    print("MATCHING ENGINE COMPARISON RESULTS")
    print("="*80)
    
    orig = comparison["original_engine"]
    enh = comparison["enhanced_engine"]
    imp = comparison["improvements"]
    
    print(f"\nORIGINAL ENGINE:")
    print(f"  Total Products: {orig['total_products']:,}")
    print(f"  Matched Products: {orig['matched_products']:,}")
    print(f"  Unmatched Products: {orig['unmatched_products']:,}")
    print(f"  Coverage: {orig['coverage_pct']:.1f}%")
    print(f"  Total Pairs: {orig['matched_pairs']:,}")
    print(f"  Perfect Pairs: {orig['perfect_pairs']:,}")
    print(f"  Similar Pairs: {orig['similar_pairs']:,}")
    
    print(f"\nENHANCED ENGINE (with {enh['embedding_model']}):")
    print(f"  Total Products: {enh['total_products']:,}")
    print(f"  Matched Products: {enh['matched_products']:,}")
    print(f"  Unmatched Products: {enh['unmatched_products']:,}")
    print(f"  Coverage: {enh['coverage_pct']:.1f}%")
    print(f"  Total Pairs: {enh['matched_pairs']:,}")
    print(f"  Perfect Pairs: {enh['perfect_pairs']:,}")
    print(f"  Similar Pairs: {enh['similar_pairs']:,}")
    
    semantic_stats = enh.get("semantic_stats", {})
    if semantic_stats:
        print(f"  Avg Semantic Similarity: {semantic_stats.get('avg_semantic_similarity', 0):.1f}")
        print(f"  Avg Lexical Similarity: {semantic_stats.get('avg_lexical_similarity', 0):.1f}")
        print(f"  High Semantic Matches (≥80): {semantic_stats.get('semantic_high_matches', 0):,}")
    
    print(f"\nIMPROVEMENTS:")
    coverage_change = imp['coverage_improvement_pct']
    coverage_symbol = "📈" if coverage_change > 0 else "📉" if coverage_change < 0 else "➡️"
    print(f"  {coverage_symbol} Coverage Change: {coverage_change:+.1f}%")
    
    matched_change = imp['additional_matched_products']
    matched_symbol = "📈" if matched_change > 0 else "📉" if matched_change < 0 else "➡️"
    print(f"  {matched_symbol} Additional Matched Products: {matched_change:+,}")
    
    unmatched_reduction = imp['reduced_unmatched_products']
    unmatched_symbol = "📈" if unmatched_reduction > 0 else "📉" if unmatched_reduction < 0 else "➡️"
    print(f"  {unmatched_symbol} Reduced Unmatched Products: {unmatched_reduction:+,}")
    
    pairs_change = imp['additional_matched_pairs']
    pairs_symbol = "📈" if pairs_change > 0 else "📉" if pairs_change < 0 else "➡️"
    print(f"  {pairs_symbol} Additional Matched Pairs: {pairs_change:+,}")
    
    reduction_pct = imp['unmatched_reduction_pct']
    print(f"  📊 Unmatched Reduction: {reduction_pct:.1f}%")
    
    print("\n" + "="*80)

def main():
    """Run comparison between original and enhanced matching engines."""
    log.info("Starting matching engine comparison...")
    
    # Run both engines
    original_success = run_original_matching()
    enhanced_success = run_enhanced_matching()
    
    if not original_success or not enhanced_success:
        log.error("One or both engines failed. Cannot perform comparison.")
        return False
    
    # Load and compare results
    original_summary, enhanced_summary = load_summary_files()
    
    if not original_summary or not enhanced_summary:
        log.error("Could not load summary files for comparison.")
        return False
    
    comparison = compare_results(original_summary, enhanced_summary)
    detailed_analysis = analyze_detailed_differences()
    
    # Save and display results
    report_file = save_comparison_report(comparison, detailed_analysis)
    print_comparison_summary(comparison)
    
    log.info(f"Comparison completed. Full report saved to: {report_file}")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
