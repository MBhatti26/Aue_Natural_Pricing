#!/usr/bin/env python3
"""
Auê Natural - Complete Data Pipeline (SIMPLIFIED)
Extract → Clean → Match → Load to Warehouse
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

VENV_PYTHON = "./venv/bin/python"

def run_step(step_name, script_path):
    """Run a pipeline step and show output"""
    print(f"\n{'='*70}")
    print(f"🚀 {step_name}")
    print(f"{'='*70}\n")
    
    result = subprocess.run([VENV_PYTHON, script_path], capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ FAILED: {step_name}")
        return False
    
    print(f"\n✅ {step_name} COMPLETED")
    return True

def main():
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║          AUÊ NATURAL - COMPLETE DATA PIPELINE                 ║
║      Extract → Clean → Match → Load to Warehouse             ║
╚═══════════════════════════════════════════════════════════════╝

Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    # Define pipeline steps
    steps = [
        ("1. EXTRACT DATA (Oxylabs)", "src/oxylabs_googleshopping_script.py"),
        ("2. CLEAN DATA", "src/cleandata_script.py"),
        ("3. MATCH PRODUCTS", "src/file_based_enhanced_matcher.py"),
        ("4. LOAD TO WAREHOUSE", "scripts/load_pipeline_to_warehouse.py"),
    ]
    
    # Run each step
    for step_name, script in steps:
        if not run_step(step_name, script):
            print(f"\n❌ PIPELINE FAILED AT: {step_name}")
            return 1
    
    # Success!
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                ✅ PIPELINE COMPLETED SUCCESSFULLY              ║
╚═══════════════════════════════════════════════════════════════╝

Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Your data warehouse is ready!
   Query it: psql -U mahnoorbhatti -d aue_warehouse

Tables:
  • aue.matched_products (product matches with prices)
  • aue.unmatched_products (products needing review)

Next steps:
  • Run analytics queries (see EER_DIAGRAM_SPEC.md)
  • Connect to PowerBI/Tableau for visualization
  • Schedule this pipeline to run daily/weekly
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
