# AUÊ NATURAL - POSTGRESQL DATA WAREHOUSE
# EER DIAGRAM SPECIFICATION (ALIGNED WITH PIPELINE)
# Database: aue_warehouse | Schema: aue
# Date: 2025-12-12

## SIMPLE TWO-TABLE DESIGN
**This schema directly reflects the actual pipeline output - NO transformations needed!**

---

## TABLES

### matched_products
**Source:** `data/processed/processed_matches.csv`  
**Purpose:** Products successfully matched between Auê Natural catalog and retailer listings

#### Primary Key:
- **match_id** (BIGSERIAL, auto-increment)

#### Product 1 Columns (Auê Natural Product):
- product_1_id (TEXT)
- product_1_name (TEXT)
- brand_1 (TEXT)
- size_value_1 (NUMERIC)
- size_unit_1 (TEXT)
- price_1 (NUMERIC(12,2))
- currency_1 (TEXT)
- date_collected_1 (TIMESTAMP)
- date_key_1 (INTEGER)
- retailer_1 (TEXT)

#### Product 2 Columns (Matched Retailer Product):
- product_2_id (TEXT)
- product_2_name (TEXT)
- brand_2 (TEXT)
- size_value_2 (NUMERIC)
- size_unit_2 (TEXT)
- price_2 (NUMERIC(12,2))
- currency_2 (TEXT)
- date_collected_2 (TIMESTAMP)
- date_key_2 (INTEGER)
- retailer_2 (TEXT)

#### Common Attributes:
- category (TEXT)

#### Similarity Scores:
- similarity (NUMERIC(5,2)) - Overall match confidence
- hybrid_name_similarity (NUMERIC(5,2))
- lexical_similarity (NUMERIC(5,2))
- semantic_similarity (NUMERIC(5,2))
- brand_similarity (NUMERIC(5,2))
- size_similarity (NUMERIC(5,2))

#### Metadata:
- import_ts (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

#### Indexes:
- idx_matched_product_1_id ON (product_1_id)
- idx_matched_product_2_id ON (product_2_id)
- idx_matched_category ON (category)
- idx_matched_date_1 ON (date_key_1)
- idx_matched_date_2 ON (date_key_2)
- idx_matched_similarity ON (similarity)

---

### unmatched_products
**Source:** `data/processed/unmatched_products.csv`  
**Purpose:** Products that could not be matched (for manual review or reprocessing)

#### Primary Key:
- **unmatched_id** (BIGSERIAL, auto-increment)

#### Product Identification:
- product_id (TEXT)
- product_name (TEXT)
- brand_id (TEXT)
- brand_name (TEXT)
- category_id (TEXT)
- category_name (TEXT)

#### Product Attributes:
- size_value (NUMERIC)
- size_unit (TEXT)
- price (NUMERIC(12,2))
- currency (TEXT)
- date_collected (TIMESTAMP)
- date_key (INTEGER)
- retailer_name (TEXT)

#### Cleaned/Normalized Fields:
- product_clean (TEXT)
- brand_clean (TEXT)
- category_clean (TEXT)
- retailer_clean (TEXT)
- size_value_norm (NUMERIC)
- size_unit_norm (TEXT)

#### Match Metadata:
- incomplete_record (BOOLEAN) - Missing required fields
- reason_unmatched (TEXT) - Why matching failed

#### Metadata:
- import_ts (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

#### Indexes:
- idx_unmatched_product_id ON (product_id)
- idx_unmatched_category ON (category_name)
- idx_unmatched_brand ON (brand_name)
- idx_unmatched_date ON (date_key)
- idx_unmatched_retailer ON (retailer_name)

---

## ANALYTICS VIEWS

### all_products
**Union of matched and unmatched products for complete catalog analysis**

Returns:
- record_type ('matched' or 'unmatched')
- product_id, product_name, brand, category
- size_value, size_unit
- price, currency, date_key, retailer
- similarity (NULL for unmatched)
- import_ts

### price_comparison
**Price differences between matched products**

Returns:
- product_1_name, brand_1, category
- retailer_1, price_1
- retailer_2, price_2
- price_diff (absolute difference)
- price_diff_pct (percentage difference)
- similarity, date_key_1

Sorted by: price_diff_pct DESC (biggest differences first)

### best_matches_by_category
**Match quality statistics grouped by category**

Returns:
- category
- match_count
- avg_similarity, min_similarity, max_similarity

Sorted by: match_count DESC

### retailer_coverage
**Retailer product catalog size and pricing**

Returns:
- retailer_name
- product_count
- category_count (distinct categories)
- avg_price

Sorted by: product_count DESC

---

## SAMPLE QUERIES

### 1. Find Biggest Price Differences
```sql
SELECT 
    product_1_name,
    retailer_1, price_1,
    retailer_2, price_2,
    price_diff_pct
FROM aue.price_comparison
WHERE ABS(price_diff_pct) > 50
ORDER BY ABS(price_diff_pct) DESC
LIMIT 20;
```

### 2. High-Confidence Matches by Category
```sql
SELECT 
    category,
    product_1_name,
    product_2_name,
    similarity
FROM aue.matched_products
WHERE similarity > 95.0
ORDER BY category, similarity DESC;
```

### 3. Products Needing Manual Review
```sql
SELECT 
    product_name,
    brand_name,
    category_name,
    retailer_name,
    reason_unmatched
FROM aue.unmatched_products
WHERE incomplete_record = FALSE
ORDER BY category_name, brand_name;
```

### 4. Retailer Price Positioning
```sql
SELECT 
    retailer_1,
    category,
    AVG(price_1) as avg_price,
    COUNT(*) as product_count
FROM aue.matched_products
GROUP BY retailer_1, category
ORDER BY category, avg_price;
```

### 5. Time-Series Price Tracking
```sql
SELECT 
    product_1_name,
    date_key_1,
    AVG(price_1) as avg_price,
    MIN(price_1) as min_price,
    MAX(price_1) as max_price,
    COUNT(DISTINCT retailer_1) as retailer_count
FROM aue.matched_products
GROUP BY product_1_name, date_key_1
ORDER BY product_1_name, date_key_1;
```

---

## DRAW.IO EER DIAGRAM

### Simple Layout:
```
┌─────────────────────────────────────────────────────────┐
│                   MATCHED_PRODUCTS                      │
│                   (Main Analysis Table)                 │
│                                                         │
│  PK: match_id (BIGSERIAL)                              │
│                                                         │
│  Product 1 (Auê Natural):                              │
│    • product_1_id, product_1_name, brand_1             │
│    • size_value_1, size_unit_1                         │
│    • price_1, currency_1, retailer_1                   │
│    • date_collected_1, date_key_1                      │
│                                                         │
│  Product 2 (Retailer):                                 │
│    • product_2_id, product_2_name, brand_2             │
│    • size_value_2, size_unit_2                         │
│    • price_2, currency_2, retailer_2                   │
│    • date_collected_2, date_key_2                      │
│                                                         │
│  Match Metrics:                                        │
│    • similarity, hybrid_name_similarity                │
│    • lexical_similarity, semantic_similarity           │
│    • brand_similarity, size_similarity                 │
│                                                         │
│  Common: category, import_ts                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                 UNMATCHED_PRODUCTS                      │
│              (Products Needing Review)                  │
│                                                         │
│  PK: unmatched_id (BIGSERIAL)                          │
│                                                         │
│  Identification:                                       │
│    • product_id, product_name                          │
│    • brand_id, brand_name                              │
│    • category_id, category_name                        │
│                                                         │
│  Attributes:                                           │
│    • size_value, size_unit                             │
│    • price, currency, retailer_name                    │
│    • date_collected, date_key                          │
│                                                         │
│  Cleaned Fields:                                       │
│    • product_clean, brand_clean                        │
│    • category_clean, retailer_clean                    │
│    • size_value_norm, size_unit_norm                   │
│                                                         │
│  Metadata:                                             │
│    • incomplete_record, reason_unmatched               │
│    • import_ts                                         │
└─────────────────────────────────────────────────────────┘
```

---

## PIPELINE INTEGRATION

### Automatic Loading After Pipeline Run:
```bash
# 1. Run extraction
python src/oxylabs_googleshopping_script.py

# 2. Run cleaning
python src/cleandata_script.py

# 3. Run matching
python src/file_based_enhanced_matcher.py

# 4. Load to warehouse (AUTOMATIC)
python scripts/load_pipeline_to_warehouse.py
```

### What Gets Loaded:
- **Input:** `data/processed/processed_matches.csv` → `aue.matched_products`
- **Input:** `data/processed/unmatched_products.csv` → `aue.unmatched_products`
- **No transformations** - direct CSV to table mapping
- **Truncate and reload** - always fresh data
- **Indexed automatically** - ready for analytics

---

## NOTES

✅ **SIMPLE:** Only 2 tables that directly match pipeline CSV output  
✅ **NO TRANSFORMATION:** CSVs load directly without mapping  
✅ **QUERYABLE:** 4 analytics views for common analysis patterns  
✅ **AUTOMATED:** One command loads entire warehouse  
✅ **TIME-SERIES READY:** date_key columns enable historical analysis  
✅ **MATCH QUALITY:** 6 similarity scores for confidence analysis  
✅ **PRICE TRACKING:** Compare prices across retailers and time  
✅ **MANUAL REVIEW:** Unmatched products identified with reasons  

🎯 **This is how a warehouse SHOULD work - aligned with your actual data!**

