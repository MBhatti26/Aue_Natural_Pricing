import os
import pandas as pd
from sqlalchemy import create_engine
import glob
from datetime import datetime

# === PostgreSQL connection details ===
user = "postgres"
password = ""  # No password needed for local trust authentication
host = "localhost"
port = 5432
database = "aue_warehouse"
schema = "aue"

# Create engine without password for local trust auth
engine = create_engine(f"postgresql+psycopg2://{user}@{host}:{port}/{database}")

# === Folder containing your CSVs ===
data_folder = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/database_to_import"

# === Find the latest timestamped CSV files ===
def get_latest_csv_files():
    """Find the most recent timestamped CSV files"""
    timestamped_files = {}
    table_types = ['retailer', 'brand', 'category', 'product', 'price_source', 'price_history']

    for table_type in table_types:
        pattern = f"{table_type}_*.csv"
        files = glob.glob(os.path.join(data_folder, pattern))
        
        if files:
            latest_file = max(files, key=os.path.getmtime)
            timestamped_files[table_type] = os.path.basename(latest_file)
            print(f"📁 Found latest {table_type} file: {os.path.basename(latest_file)}")
        else:
            print(f"⚠️ No files found for {table_type}")
    return timestamped_files

# === File-to-table mapping ===
csv_to_table = {
    'retailer': 'retailer',
    'brand': 'brand',
    'category': 'category',
    'product': 'product',
    'price_source': 'price_source',
    'price_history': 'stg_price_snapshot'  # staging table for prices
}

# === Load and import latest CSVs ===
def import_latest_csvs():
    latest_files = get_latest_csv_files()

    print(f"\n🚀 Starting import at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Found {len(latest_files)} CSV files to process\n")

    successful, failed = 0, 0

    for file_type, filename in latest_files.items():
        file_path = os.path.join(data_folder, filename)
        table_name = csv_to_table[file_type]

        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            failed += 1
            continue

        print(f"📥 Importing {filename} → {schema}.{table_name}")
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                print(f"⚠️ {filename} is empty; skipping.\n")
                failed += 1
                continue

            print(f"   📋 Columns: {list(df.columns)}")
            print(f"   📈 Rows: {len(df)}")

            # Import into PostgreSQL
            df.to_sql(table_name, con=engine, schema=schema, if_exists="replace", index=False)
            print(f"✅ Loaded {len(df)} rows into {schema}.{table_name}\n")
            successful += 1
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}\n")
            failed += 1

    print("=" * 60)
    print("📊 IMPORT SUMMARY")
    print(f"✅ Successful imports: {successful}")
    print(f"❌ Failed imports: {failed}")
    print(f"🎯 Total processed: {successful + failed}")
    print(f"⏰ Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    import_latest_csvs()
