#!/usr/bin/env python3
"""
Automated Data Processing Script for Aue Natural Pipeline
Processes new Oxylabs data and prepares it for database import
"""

import os
import sys
import glob
import shutil
import pandas as pd
from datetime import datetime
import subprocess

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from deduplication_manager import DeduplicationManager

class AueNaturalDataProcessor:
    def __init__(self, project_root="."):
        self.project_root = project_root
        self.raw_data_dir = os.path.join(project_root, "data/raw")
        self.processed_data_dir = os.path.join(project_root, "data/processed")
        self.database_import_dir = os.path.join(project_root, "database_to_import")
        self.scripts_dir = os.path.join(project_root, "src")
        self.dedup_manager = DeduplicationManager(project_root)
        
    def find_latest_raw_file(self):
        """Find the most recent raw data file"""
        pattern = os.path.join(self.raw_data_dir, "all_search_results_*.csv")
        files = glob.glob(pattern)
        if not files:
            raise FileNotFoundError("No raw data files found in data/raw/")
        
        # Sort by modification time, get the latest
        latest_file = max(files, key=os.path.getmtime)
        print(f"📁 Found latest raw file: {os.path.basename(latest_file)}")
        return latest_file
    
    def run_cleandata_script(self, input_file):
        """Run the cleandata script to process raw data"""
        script_path = os.path.join(self.scripts_dir, "cleandata_script.py")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Cleandata script not found: {script_path}")
        
        print("🔄 Running data cleaning and normalization...")
        
        # Activate virtual environment and run script
        cmd = [
            "bash", "-c",
            f"source venv/bin/activate && python {script_path} {input_file} {self.processed_data_dir}"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error running cleandata script: {result.stderr}")
            return False
        
        print("✅ Data cleaning completed successfully")
        return True
    
    def find_latest_processed_files(self):
        """Find the most recent processed files"""
        # Look for files with the latest timestamp
        pattern = os.path.join(self.processed_data_dir, "*_????????_??????.csv")
        files = glob.glob(pattern)
        
        if not files:
            raise FileNotFoundError("No processed files found")
        
        # Extract timestamps and find the latest
        timestamps = set()
        for file in files:
            basename = os.path.basename(file)
            # Extract timestamp from filename like "brand_20251104_171712.csv"
            parts = basename.split('_')
            if len(parts) >= 3:
                timestamp = f"{parts[-2]}_{parts[-1].replace('.csv', '')}"
                timestamps.add(timestamp)
        
        latest_timestamp = max(timestamps)
        print(f"📅 Latest processed timestamp: {latest_timestamp}")
        
        # Return dictionary of latest files
        file_mapping = {
            'brand': f'brand_{latest_timestamp}.csv',
            'category': f'category_{latest_timestamp}.csv',
            'price_source': f'price_source_{latest_timestamp}.csv',
            'retailer': f'retailer_{latest_timestamp}.csv',
            'product': f'product_{latest_timestamp}.csv',
            'price_history': f'price_history_{latest_timestamp}.csv'
        }
        
        return file_mapping
    
    def copy_to_database_import(self, processed_files):
        """Copy processed files to database import directory"""
        print("📋 Copying files to database import directory...")
        
        target_mapping = {
            'brand': 'brand_name.csv',
            'category': 'category_name.csv',
            'price_source': 'price_source.csv',
            'retailer': 'retailer_name.csv',
            'product': 'product.csv',
            'price_history': 'price_history.csv'
        }
        
        for file_key, source_filename in processed_files.items():
            source_path = os.path.join(self.processed_data_dir, source_filename)
            target_filename = target_mapping[file_key]
            target_path = os.path.join(self.database_import_dir, target_filename)
            
            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
                print(f"  ✅ {source_filename} → {target_filename}")
            else:
                print(f"  ❌ Source file not found: {source_filename}")
    
    def validate_data(self):
        """Validate the processed data"""
        print("🔍 Validating processed data...")
        
        files_to_check = [
            'brand_name.csv',
            'category_name.csv', 
            'price_source.csv',
            'retailer_name.csv',
            'product.csv',
            'price_history.csv'
        ]
        
        summary = {}
        for filename in files_to_check:
            filepath = os.path.join(self.database_import_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                summary[filename.replace('.csv', '')] = len(df)
                print(f"  📊 {filename}: {len(df):,} records")
            else:
                print(f"  ❌ Missing: {filename}")
                summary[filename.replace('.csv', '')] = 0
        
        return summary
    
    def generate_report(self, summary, dedup_stats=None):
        """Generate a processing report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.project_root, f"processing_report_{timestamp}.txt")
        
        with open(report_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("AUE NATURAL DATA PROCESSING REPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if dedup_stats:
                f.write("🔍 DEDUPLICATION SUMMARY:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Initial records     : {dedup_stats['initial_count']:,}\n")
                f.write(f"Duplicates removed  : {dedup_stats['duplicates_removed']:,}\n")
                f.write(f"New unique products : {dedup_stats['new_unique_products']:,}\n")
                f.write(f"Total thumbnails tracked  : {dedup_stats['total_seen_thumbnails']:,}\n\n")
            
            f.write("📊 RECORD COUNTS:\n")
            f.write("-" * 30 + "\n")
            for table, count in summary.items():
                f.write(f"{table:15}: {count:,} records\n")
            
            f.write(f"\n📁 FILES LOCATION: {self.database_import_dir}\n")
            f.write(f"🎯 STATUS: Ready for database import\n")
            f.write("=" * 60 + "\n")
        
        print(f"📄 Report generated: {report_path}")
    
    def show_database_setup_info(self):
        """Display database setup information after successful processing"""
        print("\n🗄️ DATABASE SETUP NEXT STEPS:")
        print("-" * 40)
        print("Your CSV files are ready for database import!")
        print()
        print("📁 Files location: ./database_to_import/")
        print("📋 Setup guides available:")
        print("  • DATABASE_SETUP_GUIDE.md - Complete setup instructions")
        print("  • sql/mysql_schema.sql - MySQL database schema")
        print("  • sql/mysql_import_data.sql - MySQL data import commands")
        print("  • sql/create_schema.sql - SQL Server schema (alternative)")
        print()
        print("🚀 Quick MySQL setup:")
        print("  1. mysql -u username -p")
        print("  2. CREATE DATABASE aue_natural_pricing;")
        print("  3. USE aue_natural_pricing;")
        print("  4. SOURCE sql/mysql_schema.sql;")
        print("  5. SOURCE sql/mysql_import_data.sql;")
    
    def process_new_data(self):
        """Main method to process new data"""
        try:
            print("🚀 Starting Aue Natural Data Processing Pipeline")
            print("=" * 60)
            
            # Step 1: Find latest raw data file
            latest_raw_file = self.find_latest_raw_file()
            
            # Step 2: Apply deduplication to remove previously seen products
            print("🔍 Applying deduplication to remove previously seen products...")
            dedup_file, dedup_stats = self.dedup_manager.deduplicate_raw_data(latest_raw_file)
            
            if dedup_file is None:
                print("⚠️  No new unique products found. All products were duplicates.")
                print("📊 Deduplication stats:", dedup_stats)
                return True  # Not an error, just no new data
            
            print("📊 Deduplication complete:")
            print(f"   • Initial products: {dedup_stats['initial_count']:,}")
            print(f"   • Duplicates removed: {dedup_stats['duplicates_removed']:,}")
            print(f"   • New unique products: {dedup_stats['new_unique_products']:,}")
            print(f"   • Total thumbnails tracked: {dedup_stats['total_seen_thumbnails']:,}")
            
            # Step 3: Run cleandata script on deduplicated data
            if not self.run_cleandata_script(dedup_file):
                return False
            
            # Step 4: Find latest processed files
            processed_files = self.find_latest_processed_files()
            
            # Step 5: Copy to database import directory
            self.copy_to_database_import(processed_files)
            
            # Step 6: Validate data
            summary = self.validate_data()
            
            # Step 7: Generate report (include deduplication stats)
            self.generate_report(summary, dedup_stats)
            
            # Step 8: Show database setup info
            self.show_database_setup_info()
            
            print("=" * 60)
            print("🎉 Data processing pipeline completed successfully!")
            print("📋 Files are ready for database import")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in data processing pipeline: {str(e)}")
            return False

if __name__ == "__main__":
    processor = AueNaturalDataProcessor()
    success = processor.process_new_data()
    sys.exit(0 if success else 1)
