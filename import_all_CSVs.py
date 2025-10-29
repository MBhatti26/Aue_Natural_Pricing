import os
import pandas as pd
from sqlalchemy import create_engine

# === MySQL connection details ===
user = "root"
password = "beauty123"
host = "127.0.0.1"
port = 3307
database = "beauty_price_tracker"

# create connection
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")

# === Folder containing your CSVs ===
data_folder = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/database_to_import"

# === Mapping of files → table names ===
csv_to_table = {
    "retailer_name.csv": "retailers",
    "brand_name.csv": "brands",
    "category_name.csv": "categories",
    "product.csv": "products",
    "price_source.csv": "price_source",
    "price_history.csv": "price_history"
}

# === Import each CSV ===
for filename, table_name in csv_to_table.items():
    file_path = os.path.join(data_folder, filename)

    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        continue

    print(f"📥 Importing {filename} → Table: {table_name}")

    try:
        df = pd.read_csv(file_path)
        df.to_sql(table_name, con=engine, if_exists="replace", index=False)
        print(f"✅ Loaded {len(df)} rows into '{table_name}'\n")

    except Exception as e:
        print(f"❌ Error loading {filename}: {e}\n")

print("🎉 All available CSVs imported into MySQL!")
