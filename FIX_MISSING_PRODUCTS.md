# 🔍 Root Cause Analysis: Missing Products in Match Results

**Date:** December 1, 2025  
**Issue:** Match results dropped from ~1000+ to only 78 matched + 97 unmatched  
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## 📊 THE PROBLEM

### Current State:
- **Raw CSV (latest):** 1,015 products (Nov 25, 2025)
- **Database CSVs:** 888 products (Nov 8, 2025) 
- **PostgreSQL DB:** 960 price snapshots (Nov 8, 2025)
- **Match Results:** Only 78 matched + 97 unmatched = 175 total

### Expected State:
- Should be matching ~1,015 products from latest extraction
- Should have ~888 matched + remaining unmatched = ~1,000 total results

---

## 🔍 ROOT CAUSE

**The enhanced matching engine is querying OUTDATED data from PostgreSQL!**

### Evidence:

1. **PostgreSQL staging table is from November 8th:**
   ```sql
   SELECT date_collected, COUNT(*) FROM aue.stg_price_snapshot 
   GROUP BY date_collected ORDER BY date_collected DESC LIMIT 5;
   
   date_collected  | count 
   -----------------+-------
   20251108_121547 |    20
   20251108_121535 |    40
   ```

2. **Latest raw CSV is from November 25th:**
   ```bash
   data/raw/all_search_results_20251125_201913.csv  (1,015 rows, 8.8MB)
   ```

3. **Database import files are also from November 8th:**
   ```bash
   database_to_import/product_20251108_121845.csv  (888 products)
   database_to_import/price_history_20251108_121845.csv
   ```

4. **The matching engine queries PostgreSQL, not CSVs:**
   ```python
   # From src/enhanced_matching_engine.py line 340-371
   query = f"""
       SELECT 
           p.product_id,
           p.product_name,
           ...
       FROM {SCHEMA}.product p
       LEFT JOIN {SCHEMA}.stg_price_snapshot s
           ON p.product_id = s.product_id
       ...
   """
   df = pd.read_sql(query, con=engine)  # <-- QUERIES OLD DB!
   ```

---

## ✅ THE SOLUTION

### Step 1: Reload PostgreSQL with Latest Data

**Run the database reload script:**

```bash
cd /Users/mahnoorbhatti/Desktop/Final_Project_Aue_Natural

# First, update the password in the reload script
# Edit scripts/reload_postgres_db.py line 9:
# password = "your_actual_postgres_password"

# Then run it:
python scripts/reload_postgres_db.py
```

This will:
- Find the latest timestamped CSV files in `database_to_import/`
- Load them into PostgreSQL `aue_warehouse.aue` schema
- Replace old data with new data

**Expected output:**
```
📁 Found latest retailer file: retailer_20251108_121845.csv
📁 Found latest product file: product_20251108_121845.csv
...
✅ Loaded 888 rows into aue.product
✅ Loaded 960 rows into aue.stg_price_snapshot
```

### Step 2: Re-run the Matching Engine

```bash
python src/enhanced_matching_engine.py
```

This should now:
- Query the updated PostgreSQL database
- Match against all 888 products in the catalog
- Generate ~888 matched results + remaining unmatched
- Output to `data/processed/processed_matches.csv`

---

## 🤔 WHY THIS HAPPENED

1. **Data extraction workflow:**
   - Oxylabs API → `data/raw/*.csv` (gets updated frequently)
   - Raw CSV → cleaning → `database_to_import/*.csv` (manual step)
   - Import CSVs → PostgreSQL (manual step via reload script)

2. **The gap:**
   - New raw data was extracted (Nov 25)
   - But database import CSVs were never updated from Nov 8
   - PostgreSQL was never reloaded with new data
   - Matching engine queries old PostgreSQL data

3. **The fix broke nothing:**
   - We added date_key, date_dim, etc. successfully
   - But we were always querying OLD data
   - So our improvements worked, just on outdated dataset

---

## 🔧 IMMEDIATE ACTION REQUIRED

**TO GET YOUR ~1000 RESULTS BACK:**

1. First, you need to **regenerate the database import CSVs** from the latest raw data:
   ```bash
   # Run the data cleaning script on the latest raw CSV
   python src/cleandata_script.py
   ```
   This should create new timestamped CSVs in `database_to_import/`

2. Then **reload PostgreSQL** with the new data:
   ```bash
   # Update password first in scripts/reload_postgres_db.py
   python scripts/reload_postgres_db.py
   ```

3. Finally, **re-run the matching engine:**
   ```bash
   python src/enhanced_matching_engine.py
   ```

---

## 📝 TECHNICAL NOTES

### Database Tables Affected:
- `aue.product` (888 rows)
- `aue.brand` 
- `aue.category`
- `aue.retailer`
- `aue.price_source`
- `aue.stg_price_snapshot` (960 rows) ← **This is what matching engine queries**

### Why PostgreSQL Matters:
The enhanced matching engine uses PostgreSQL because:
1. It pre-joins product + brand + category + retailer + price
2. This creates a denormalized view for faster matching
3. Eliminates need to join CSVs on every run

**Trade-off:**
- ✅ Faster matching (SQL joins vs pandas merges)
- ❌ Requires manual DB reload step when data changes

---

## 🎯 VERIFICATION CHECKLIST

After running the fix, verify:

- [ ] PostgreSQL has latest data: 
  ```sql
  SELECT MAX(date_collected) FROM aue.stg_price_snapshot;
  -- Should show 2025-11-25 or later
  ```

- [ ] Match results increased:
  ```bash
  wc -l data/processed/processed_matches.csv
  # Should be ~888 + header = 889 lines
  ```

- [ ] Unmatched products present:
  ```bash
  wc -l data/processed/unmatched_products.csv
  # Should be ~127 (1015 raw - 888 matched)
  ```

- [ ] Date fields populated correctly:
  ```bash
  head data/processed/processed_matches.csv
  # Check date_collected and date_key columns present
  ```

---

**Status:** 🔴 REQUIRES ACTION  
**Priority:** 🔥 HIGH - Blocks all matching results  
**ETA:** ~10 minutes to fix (clean data + reload DB + re-run matching)
