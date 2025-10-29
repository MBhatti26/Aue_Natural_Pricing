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

# --- Confidence scoring ---
def compute_confidence(row1, row2, name_weight=0.7, brand_weight=0.2, price_weight=0.1):
    name_score = fuzz.token_set_ratio(row1["product_clean"], row2["product_clean"])
    brand_score = fuzz.ratio(row1["brand_clean"], row2["brand_clean"])

    # price similarity
    if pd.notna(row1["price"]) and pd.notna(row2["price"]) and row1["price"] > 0 and row2["price"] > 0:
        diff_ratio = abs(row1["price"] - row2["price"]) / max(row1["price"], row2["price"])
        price_score = max(0, 100 * (1 - diff_ratio))
    else:
        price_score = 50  # fallback mid score

    return round(name_weight * name_score + brand_weight * brand_score + price_weight * price_score, 2)

# --- Matching pass ---
subset = df.copy()   # use full dataset or .head(500) for test
matches = []
threshold = 90

print("🔍 Computing fuzzy matches...")

for i, r1 in subset.iterrows():
    for j, r2 in subset.iloc[i + 1 :].iterrows():
        # Skip self-matches
        if r1["product_id"] == r2["product_id"]:
            continue

        # Require same category or strong brand overlap
        brand_sim = fuzz.ratio(r1["brand_clean"], r2["brand_clean"])
        if (r1["category_id"] != r2["category_id"]) and (brand_sim < 85):
            continue

        # Skip generic short names
        if len(r1["product_name"].split()) < 3 or len(r2["product_name"].split()) < 3:
            continue

        # Price sanity filter
        if pd.notna(r1["price"]) and pd.notna(r2["price"]):
            price_diff = abs(r1["price"] - r2["price"]) / max(r1["price"], r2["price"])
            if price_diff > 0.3:
                continue

        # Compute confidence
        score = compute_confidence(r1, r2)
        if score >= threshold:
            matches.append({
                "product_1_id": r1["product_id"],
                "product_2_id": r2["product_id"],
                "product_1_name": r1["product_name"],
                "product_2_name": r2["product_name"],
                "price_1": r1["price"],
                "price_2": r2["price"],
                "currency_1": r1["currency"],
                "currency_2": r2["currency"],
                "retailer_1": r1["retailer_name"],
                "retailer_2": r2["retailer_name"],
                "similarity": score
            })

matches_df = pd.DataFrame(matches)
print(f"✅ Found {len(matches_df)} potential matches above {threshold}% similarity.")

# --- Remove duplicates (e.g. A↔B vs B↔A) ---
matches_df["pair_key"] = matches_df.apply(lambda x: "_".join(sorted([x["product_1_id"], x["product_2_id"]])), axis=1)
matches_df = matches_df.drop_duplicates(subset="pair_key").drop(columns=["pair_key"])

# --- Sort and save ---
matches_df = matches_df.sort_values(by="similarity", ascending=False).reset_index(drop=True)

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
