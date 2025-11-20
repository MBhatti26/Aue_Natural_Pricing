#!/usr/bin/env python3
"""
Production-Ready Enhanced Matching Engine with Consolidated Output

This is the main production matching engine that:
1. Uses hybrid lexical + semantic similarity with vector embeddings
2. Includes post-processing for additional match recovery  
3. Outputs a single consolidated BI-ready CSV file
4. Avoids generating redundant multiple CSV files
"""

import os
import subprocess
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("production_matcher")

def run_enhanced_engine():
    """Run the enhanced matching engine."""
    log.info("Running enhanced matching engine with embeddings...")
    try:
        result = subprocess.run([
            sys.executable, "src/enhanced_matching_engine.py"
        ], capture_output=True, text=True, check=True)
        log.info("Enhanced matching engine completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Enhanced matching engine failed: {e}")
        log.error(f"Stderr: {e.stderr}")
        return False

def run_post_processing():
    """Run post-processing to catch additional matches."""
    log.info("Running post-processing for additional match recovery...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/post_process_unmatched.py"
        ], capture_output=True, text=True, check=True)
        log.info("Post-processing completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Post-processing failed: {e}")
        log.error(f"Stderr: {e.stderr}")
        return False

def run_consolidation():
    """Run output consolidation to create BI-ready files."""
    log.info("Consolidating outputs into BI-ready format...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/consolidate_outputs.py"
        ], capture_output=True, text=True, check=True)
        log.info("Output consolidation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Output consolidation failed: {e}")
        log.error(f"Stderr: {e.stderr}")
        return False

def main():
    """Run the complete production matching pipeline."""
    
    log.info("="*80)
    log.info("🚀 STARTING PRODUCTION MATCHING PIPELINE")
    log.info("="*80)
    
    start_time = datetime.now()
    
    # Step 1: Enhanced matching engine
    if not run_enhanced_engine():
        log.error("❌ Enhanced matching engine failed - aborting pipeline")
        return False
    
    # Step 2: Post-processing recovery
    if not run_post_processing():
        log.error("❌ Post-processing failed - aborting pipeline") 
        return False
    
    # Step 3: Output consolidation
    if not run_consolidation():
        log.error("❌ Output consolidation failed - aborting pipeline")
        return False
    
    # Success summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    log.info("="*80)
    log.info("✅ PRODUCTION MATCHING PIPELINE COMPLETED SUCCESSFULLY")
    log.info("="*80)
    log.info(f"⏱️  Total processing time: {duration}")
    log.info("📁 Output files:")
    log.info("   - processed_matches_YYYYMMDD_HHMMSS.csv (main output)")
    log.info("   - unmatched_products_YYYYMMDD_HHMMSS.csv (remaining unmatched)")  
    log.info("   - processing_summary_YYYYMMDD_HHMMSS.json (statistics)")
    log.info("="*80)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
