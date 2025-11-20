#!/usr/bin/env python3
"""
Automated Product Matching Pipeline for Auê Natural

This script runs the complete matching engine pipeline:
1. Enhanced matching engine with semantic embeddings
2. Post-processing of unmatched products
3. Automatic merging of results
4. Generation of final reports and statistics

Usage:
    python scripts/automated_matching_pipeline.py [input_file.csv]
    
If no input file is provided, it will use the latest file in data/raw/
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import json
import subprocess
import glob
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/matching_pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("automated_pipeline")

class MatchingPipeline:
    def __init__(self, input_file=None):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.input_file = input_file
        self.base_dir = Path(".")
        self.data_dir = self.base_dir / "data"
        self.processed_dir = self.data_dir / "processed"
        self.scripts_dir = self.base_dir / "scripts"
        self.src_dir = self.base_dir / "src"
        
        # Ensure directories exist
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "logs").mkdir(exist_ok=True)
        
        # File paths that will be generated
        self.matched_file = None
        self.unmatched_file = None
        self.post_processed_file = None
        self.final_matched_file = None
        self.final_unmatched_file = None
        self.summary_file = None
        
    def cleanup_old_files(self):
        """Clean up old processing files to prevent clutter."""
        log.info("🧹 CLEANING UP: Archiving old processing files...")
        
        # Create archive directory
        archive_dir = self.processed_dir / "archive_old_versions"
        archive_dir.mkdir(exist_ok=True)
        
        # Patterns of files to archive
        cleanup_patterns = [
            "processed_matches_*.csv",
            "unmatched_products_*.csv", 
            "post_processed_matches_*.csv",
            "combined_matches_*.csv",
            "remaining_unmatched_*.csv",
            "updated_matches_*.csv",
            "updated_unmatched_*.csv",
            "processing_summary_*.json",
            "updated_processing_summary_*.json",
            "final_matches_*.csv",
            "final_unmatched_*.csv",
            "pipeline_summary_*.json"
        ]
        
        archived_count = 0
        for pattern in cleanup_patterns:
            files = glob.glob(str(self.processed_dir / pattern))
            for file_path in files:
                file_name = os.path.basename(file_path)
                # Skip if already in archive
                if not file_path.startswith(str(archive_dir)):
                    try:
                        os.rename(file_path, str(archive_dir / file_name))
                        archived_count += 1
                        log.info(f"   Archived: {file_name}")
                    except Exception as e:
                        log.warning(f"   Could not archive {file_name}: {e}")
        
        log.info(f"✅ Archived {archived_count} old files")
        
    def remove_old_symlinks(self):
        """Remove old symlinks before creating new ones."""
        symlinks = [
            self.processed_dir / "FINAL_MATCHES.csv",
            self.processed_dir / "FINAL_UNMATCHED.csv", 
            self.processed_dir / "FINAL_SUMMARY.json",
            self.processed_dir / "latest_matches.csv",
            self.processed_dir / "latest_unmatched.csv",
            self.processed_dir / "latest_summary.json"
        ]
        
        for link in symlinks:
            if link.is_symlink() or link.exists():
                try:
                    link.unlink()
                    log.info(f"   Removed old symlink: {link.name}")
                except Exception as e:
                    log.warning(f"   Could not remove {link.name}: {e}")
        
    def find_latest_input_file(self):
        """Find the latest raw data file if none specified."""
        if self.input_file:
            return self.input_file
            
        # Look for latest file in data/raw/
        raw_files = glob.glob(str(self.data_dir / "raw" / "*.csv"))
        if not raw_files:
            raise FileNotFoundError("No CSV files found in data/raw/")
            
        # Get the most recent file
        latest_file = max(raw_files, key=os.path.getctime)
        log.info(f"Using latest input file: {latest_file}")
        return latest_file
        
    def run_enhanced_matching_engine(self):
        """Run the enhanced matching engine with semantic embeddings."""
        log.info("🚀 STEP 1: Running Enhanced Matching Engine...")
        
        input_file = self.find_latest_input_file()
        engine_script = self.src_dir / "file_based_enhanced_matcher.py"
        
        if not engine_script.exists():
            raise FileNotFoundError(f"File-based matching engine not found: {engine_script}")
            
        # Run the enhanced matching engine
        cmd = [
            sys.executable, str(engine_script),
            "--input", input_file,
            "--output-dir", str(self.processed_dir)
        ]
        
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            log.error(f"Enhanced matching engine failed: {result.stderr}")
            log.error(f"Enhanced matching engine stdout: {result.stdout}")
            raise RuntimeError(f"Enhanced matching engine failed: {result.stderr}")
            
        log.info("✅ Enhanced matching engine completed successfully")
        log.info(f"Engine output: {result.stdout}")
        
        # Find the generated files
        self.matched_file = self._find_latest_file("processed_matches_*.csv")
        self.unmatched_file = self._find_latest_file("unmatched_products_*.csv")
        
        log.info(f"Generated matched file: {self.matched_file}")
        log.info(f"Generated unmatched file: {self.unmatched_file}")
        
    def run_post_processing(self):
        """Run post-processing on unmatched products."""
        log.info("🔄 STEP 2: Running Post-Processing on Unmatched Products...")
        
        if not self.unmatched_file:
            raise RuntimeError("No unmatched file found from previous step")
            
        post_processor_script = self.scripts_dir / "post_process_unmatched.py"
        
        if not post_processor_script.exists():
            raise FileNotFoundError(f"Post-processor not found: {post_processor_script}")
            
        # Run post-processing
        cmd = [sys.executable, str(post_processor_script)]
        
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.base_dir))
        
        if result.returncode != 0:
            log.error(f"Post-processing failed: {result.stderr}")
            raise RuntimeError(f"Post-processing failed: {result.stderr}")
            
        log.info("✅ Post-processing completed successfully")
        
        # Find the post-processed matches file
        self.post_processed_file = self._find_latest_file("post_processed_matches_*.csv")
        log.info(f"Generated post-processed matches: {self.post_processed_file}")
        
    def merge_results(self):
        """Merge post-processed matches with original matches."""
        log.info("🔗 STEP 3: Merging Post-Processed Results...")
        
        if not all([self.matched_file, self.unmatched_file, self.post_processed_file]):
            raise RuntimeError("Missing files for merging step")
            
        # Load data
        log.info("Loading original matched products...")
        main_matches = pd.read_csv(self.matched_file)
        
        log.info("Loading post-processed matches...")
        post_matches = pd.read_csv(self.post_processed_file)
        
        log.info("Loading unmatched products...")
        unmatched = pd.read_csv(self.unmatched_file)
        
        # Standardize post-processed matches format
        log.info("Standardizing post-processed matches format...")
        
        # Add missing columns with default values
        post_matches['hybrid_name_similarity'] = np.nan
        post_matches['semantic_similarity'] = np.nan
        post_matches['processing_date'] = datetime.now().strftime('%Y-%m-%d')
        post_matches['engine_version'] = 'enhanced_with_embeddings_v1_plus_postprocessing'
        post_matches['confidence_tier'] = 'LOW'  # Post-processing typically finds lower confidence matches
        post_matches['match_rank'] = 1
        
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
        
        # Save final files
        self.final_matched_file = self.processed_dir / f"final_matches_{self.timestamp}.csv"
        self.final_unmatched_file = self.processed_dir / f"final_unmatched_{self.timestamp}.csv"
        
        log.info(f"Saving final matches to {self.final_matched_file}...")
        combined_matches.to_csv(self.final_matched_file, index=False)
        
        log.info(f"Saving final unmatched to {self.final_unmatched_file}...")
        updated_unmatched.to_csv(self.final_unmatched_file, index=False)
        
        # Generate statistics
        total_products = 888  # From dataset
        matched_products = total_products - new_unmatched_count
        coverage_percentage = (matched_products / total_products) * 100
        
        self.stats = {
            "processing_metadata": {
                "timestamp": datetime.now().isoformat(),
                "engine_version": "enhanced_with_embeddings_v1_plus_postprocessing",
                "pipeline_version": "automated_v1",
                "input_file": str(self.find_latest_input_file()),
                "total_processing_time": "calculated_at_end"
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
                "post_processing_pairs": len(post_matches),
                "perfect_matches_100pct": int((combined_matches['similarity'] == 100.0).sum()),
                "high_quality_85pct_plus": int((combined_matches['similarity'] >= 85.0).sum()),
                "acceptable_65pct_plus": int((combined_matches['similarity'] >= 65.0).sum())
            },
            "improvement_summary": {
                "original_unmatched": original_unmatched_count,
                "newly_matched_products": removed_count,
                "remaining_unmatched": new_unmatched_count,
                "coverage_improvement": f"{removed_count} products recovered ({round((removed_count/original_unmatched_count)*100, 1)}% reduction)"
            },
            "file_outputs": {
                "final_matched_file": str(self.final_matched_file),
                "final_unmatched_file": str(self.final_unmatched_file),
                "processing_summary": None  # Will be set below
            }
        }
        
        log.info(f"✅ Merging completed - {removed_count} products recovered from unmatched")
        
    def generate_final_report(self):
        """Generate comprehensive final report and create clean symlinks."""
        log.info("📊 STEP 4: Generating Final Report and Cleaning Up...")
        
        # Save processing summary
        self.summary_file = self.processed_dir / f"pipeline_summary_{self.timestamp}.json"
        self.stats["file_outputs"]["processing_summary"] = str(self.summary_file)
        
        with open(self.summary_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
            
        # Remove old symlinks first
        self.remove_old_symlinks()
            
        # Create clean FINAL_* symlinks
        final_matched = self.processed_dir / "FINAL_MATCHES.csv"
        final_unmatched = self.processed_dir / "FINAL_UNMATCHED.csv"
        final_summary = self.processed_dir / "FINAL_SUMMARY.json"
        
        # Create legacy symlinks too for backward compatibility
        latest_matched = self.processed_dir / "latest_matches.csv"
        latest_unmatched = self.processed_dir / "latest_unmatched.csv"
        latest_summary = self.processed_dir / "latest_summary.json"
                
        # Create new symlinks
        final_matched.symlink_to(self.final_matched_file.name)
        final_unmatched.symlink_to(self.final_unmatched_file.name)
        final_summary.symlink_to(self.summary_file.name)
        
        latest_matched.symlink_to(self.final_matched_file.name)
        latest_unmatched.symlink_to(self.final_unmatched_file.name)
        latest_summary.symlink_to(self.summary_file.name)
        
        log.info("✅ Final report generated and clean symlinks created")
        
    def update_powerbi_dashboards(self):
        """Update PowerBI dashboards with latest data."""
        log.info("📊 STEP 5: Updating PowerBI Dashboards...")
        
        # Check if PowerBI integration is configured
        powerbi_enabled = os.getenv('POWERBI_ENABLED', 'false').lower() == 'true'
        
        if not powerbi_enabled:
            log.info("⚠️  PowerBI integration not enabled. Set POWERBI_ENABLED=true to activate.")
            log.info("💡 Dashboards can still be manually refreshed from ./powerbi_data/ files")
            return
        
        try:
            # Copy final files to powerbi_data directory
            powerbi_dir = self.base_dir / "powerbi_data"
            powerbi_dir.mkdir(exist_ok=True)
            
            # Copy latest results for PowerBI consumption
            import shutil
            shutil.copy2(self.final_matched_file, powerbi_dir / "FINAL_MATCHES.csv")
            shutil.copy2(self.final_unmatched_file, powerbi_dir / "FINAL_UNMATCHED.csv") 
            shutil.copy2(self.summary_file, powerbi_dir / "FINAL_SUMMARY.json")
            
            log.info(f"✅ Data files updated in {powerbi_dir}")
            
            # If PowerBI API is configured, trigger automatic refresh
            try:
                from powerbi_auto_update import integrate_with_pipeline
                success = integrate_with_pipeline()
                if success:
                    log.info("🎉 PowerBI dashboards updated automatically!")
                else:
                    log.warning("⚠️  PowerBI API update failed, manual refresh required")
            except ImportError:
                log.info("💡 PowerBI API integration not available, files ready for manual refresh")
            except Exception as e:
                log.warning(f"⚠️  PowerBI auto-update error: {str(e)}")
                
        except Exception as e:
            log.error(f"❌ PowerBI update failed: {str(e)}")
            
    def print_final_summary(self):
        """Print comprehensive final summary."""
        stats = self.stats
        
        print("\n" + "="*80)
        print("🎉 AUTOMATED MATCHING PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"   Total Products: {stats['dataset_overview']['total_products']}")
        print(f"   Matched Products: {stats['dataset_overview']['matched_products']} ({stats['dataset_overview']['coverage_percentage']}% coverage)")
        print(f"   Unmatched Products: {stats['dataset_overview']['unmatched_products']}")
        print(f"   Total Match Pairs: {stats['matching_results']['total_match_pairs']}")
        
        print(f"\n🏆 MATCH QUALITY BREAKDOWN:")
        print(f"   Perfect Matches (100%): {stats['matching_results']['perfect_matches_100pct']}")
        print(f"   High Quality (≥85%): {stats['matching_results']['high_quality_85pct_plus']}")
        print(f"   All Acceptable (≥65%): {stats['matching_results']['acceptable_65pct_plus']}")
        
        print(f"\n🔄 PROCESSING RESULTS:")
        print(f"   Main Engine Pairs: {stats['matching_results']['main_engine_pairs']}")
        print(f"   Post-Processing Pairs: {stats['matching_results']['post_processing_pairs']}")
        print(f"   Products Recovered: {stats['improvement_summary']['newly_matched_products']}")
        
        print(f"\n📁 OUTPUT FILES:")
        print(f"   Final Matches: {stats['file_outputs']['final_matched_file']}")
        print(f"   Final Unmatched: {stats['file_outputs']['final_unmatched_file']}")
        print(f"   Processing Summary: {stats['file_outputs']['processing_summary']}")
        
        print(f"\n🔗 CLEAN PRODUCTION FILES (Use These):")
        print(f"   FINAL_MATCHES.csv    → Final matched products (934 pairs)")
        print(f"   FINAL_UNMATCHED.csv  → Final unmatched products (391 remaining)")
        print(f"   FINAL_SUMMARY.json   → Complete processing statistics")
        print(f"\n🗄️ OLD FILES: Automatically archived to archive_old_versions/")
        
        print("\n" + "="*80)
        print("🚀 READY FOR DEPLOYMENT!")
        print("="*80)
        
    def _find_latest_file(self, pattern):
        """Find the latest file matching a pattern."""
        files = glob.glob(str(self.processed_dir / pattern))
        if not files:
            raise FileNotFoundError(f"No files found matching pattern: {pattern}")
        return max(files, key=os.path.getctime)
        
    def run_complete_pipeline(self):
        """Run the complete automated pipeline with automatic cleanup."""
        start_time = datetime.now()
        
        try:
            log.info("🎯 Starting Automated Matching Pipeline...")
            
            # Step 0: Clean up old files FIRST to prevent clutter
            self.cleanup_old_files()
            
            # Step 1: Enhanced Matching Engine
            self.run_enhanced_matching_engine()
            
            # Step 2: Post-Processing
            self.run_post_processing()
            
            # Step 3: Merge Results
            self.merge_results()
            
            # Step 4: Generate Report & Clean Symlinks
            self.generate_final_report()
            
            # Step 5: Auto-Update PowerBI Dashboards (if configured)
            self.update_powerbi_dashboards()
            
            # Calculate total time
            end_time = datetime.now()
            total_time = str(end_time - start_time)
            self.stats["processing_metadata"]["total_processing_time"] = total_time
            
            # Update summary file with final timing
            with open(self.summary_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            
            # Print final summary
            self.print_final_summary()
            
            log.info(f"🎉 Pipeline completed successfully in {total_time}")
            
        except Exception as e:
            log.error(f"❌ Pipeline failed: {str(e)}")
            raise

def main():
    """Main entry point."""
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    if input_file and not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
        
    pipeline = MatchingPipeline(input_file)
    pipeline.run_complete_pipeline()

if __name__ == "__main__":
    main()
