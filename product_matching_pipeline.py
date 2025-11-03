import pandas as pd
from sqlalchemy import create_engine
from rapidfuzz import fuzz
import re
import time

start = time.time()

# === MySQL connection ===
user = "root"
password = "beauty123"
host = "127.0.0.1"
port = 3307
database = "beauty_price_tracker"

engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")

# === Load merged data from DB ===
query = """
SELECT 
    p.product_id,
    p.product_name,
    p.brand_id,
    p.category_id,
    p.size_value,
    p.size_unit,
    ph.price,
    ph.currency,
    r.retailer_name
FROM products p
LEFT JOIN price_history ph ON p.product_id = ph.product_id
LEFT JOIN retailers r ON ph.retailer_id = r.retailer_id
"""
df = pd.read_sql(query, con=engine)
print(f"✅ Loaded {len(df)} product-price-retailer rows from MySQL.")

# --- Cleaning ---
def normalize(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text)

df["product_clean"] = df["product_name"].apply(normalize)
df["brand_clean"] = df["brand_id"].astype(str).apply(normalize)
df["category_clean"] = df["category_id"].astype(str).apply(normalize)
df["retailer_name"] = df["retailer_name"].astype(str).str.lower().str.strip()

# --- Identify unmatched products ---
all_ids = set(df["product_id"])
matched_ids = set(matches_df["product_1_id"]) | set(matches_df["product_2_id"])
unmatched_ids = all_ids - matched_ids

unmatched_df = df[df["product_id"].isin(unmatched_ids)].copy()
unmatched_df["reason_unmatched"] = "No match >= threshold"

# --- Save outputs ---
unmatched_path = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/unmatched_products_v3.csv"
matches_path = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/matched_products_clean_v3.csv"

unmatched_df.to_csv(unmatched_path, index=False)
matches_df.to_csv(matches_path, index=False)

print(f"💾 Saved cleaned pairwise matches → {matches_path}")
print(f"📉 Saved {len(unmatched_df)} unmatched products → {unmatched_path}")

# --- Optional: best match summary per product ---
best_match = matches_df.loc[matches_df.groupby("product_1_id")["similarity"].idxmax()]
best_path = "/Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural/best_match_summary_v3.csv"
best_match.to_csv(best_path, index=False)
print(f"📈 Saved top match per product → {best_path}")

# --- Save to MySQL ---
matches_df.to_sql("product_match_results_v3", con=engine, if_exists="replace", index=False)
best_match.to_sql("product_best_match_summary", con=engine, if_exists="replace", index=False)

end = time.time()
print(f"⏱️ Runtime: {round(end - start, 2)} seconds")
print("🎯 Matching pipeline complete.")
