#!/usr/bin/env python3
"""
Auê Natural - Complete Data Pipeline
Simple, clean, end-to-end execution
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

VENV_PYTHON = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/venv/bin/python"

def run_step(step_name, script_path, args=None):
    """Run a pipeline step"""
    print(f"\n{'='*70}")
    print(f"🚀 STEP: {step_name}")
    print(f"{'='*70}")
    
    cmd = [VENV_PYTHON, script_path]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ FAILED: {step_name}")
        print(result.stderr)
        return False
    
    print(result.stdout)
    print(f"✅ COMPLETED: {step_name}")
    return True

def main():
    """Run complete pipeline"""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                  AUÊ NATURAL DATA PIPELINE                       ║
║                    End-to-End Execution                          ║
╚══════════════════════════════════════════════════════════════════╝

Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    steps = [
        # Step 1: Data Extraction (optional - can use existing data)
        # ("Extract Data", "src/oxylabs_googleshopping_script.py"),
        
        # Step 2: Clean Data
        ("Clean Data", "src/cleandata_script.py", ["data/raw/latest_data.csv"]),
        
        # Step 3: Match Products
        ("Match Products", "src/file_based_enhanced_matcher.py"),
        
        # Step 4: Consolidate to Master CSVs
        ("Consolidate CSVs", "scripts/master_csv_manager.py"),
        
        # Step 5: Load to PostgreSQL
        ("Load Database", "scripts/load_master_csvs_to_postgres.py"),
    ]
    
    for step_data in steps:
        if len(step_data) == 3:
            step_name, script, args = step_data
            if not run_step(step_name, script, args):
                print(f"\n❌ Pipeline failed at: {step_name}")
                return 1
        else:
            step_name, script = step_data
            if not run_step(step_name, script):
                print(f"\n❌ Pipeline failed at: {step_name}")
                return 1
    
    print(f"""
{'='*70}
✅ PIPELINE COMPLETED SUCCESSFULLY
{'='*70}

Data is now in PostgreSQL database: aue_warehouse
Master CSVs in: database_to_import/

Next steps:
  1. Run SQL queries for analysis
  2. Connect to PowerBI/Tableau for dashboards
  3. Schedule pipeline with cron/airflow

""")
    return 0

if __name__ == "__main__":
    sys.exit(main())
