# Data Directory Structure

## Overview
This directory contains all data files organized by processing stage.

## Directory Structure

```
data/
├── raw/                           # Raw scraped data from Oxylabs
│   └── all_search_results_*.csv   # Timestamped raw Google Shopping data
│
├── processed/                     # Processed and normalized data
│   ├── intermediate/              # Intermediate cleaned files (single table format)
│   │   └── cleaned_products_*.csv # Basic cleaned data with extracted fields
│   │
│   ├── brand_*.csv               # Normalized brand dimension table
│   ├── category_*.csv            # Normalized category dimension table
│   ├── retailer_*.csv            # Normalized retailer dimension table
│   ├── product_*.csv             # Normalized product dimension table
│   ├── price_source_*.csv        # Normalized price source dimension table
│   ├── price_history_*.csv       # Normalized price fact table
│   │
│   ├── matched_products_*.csv    # Product matching results
│   ├── perfect_matches_*.csv     # Perfect product matches
│   ├── similar_matches_*.csv     # Similar product matches
│   ├── unmatched_products_*.csv  # Unmatched products
│   └── best_match_summary_*.csv  # Best match summary
│
└── logs/                         # Processing logs and deduplication state
    ├── seen_urls.json           # Deduplication state: URLs
    ├── seen_thumbnails.json     # Deduplication state: Thumbnails  
    └── seen_product_ids.json    # Deduplication state: Product IDs
```

## File Types

### Raw Data (`data/raw/`)
- **Source**: Oxylabs Google Shopping API
- **Format**: Single CSV with all product data
- **Columns**: pos, url, title, price, merchant, thumbnail, etc.

### Intermediate Cleaned (`data/processed/intermediate/`)
- **Source**: Basic cleandata_script.py processing
- **Format**: Single CSV with extracted and cleaned fields
- **Purpose**: Temporary files with brand extraction, size parsing, etc.
- **Columns**: Original columns + brand_clean, product_clean, size_value, etc.

### Normalized Tables (`data/processed/`)
- **Source**: Archive cleandata_script.py (normalization)
- **Format**: Separate CSV files for each database table
- **Purpose**: Database-ready normalized tables
- **Ready for import**: Into PostgreSQL via load_to_db.py

### Matching Results (`data/processed/`)
- **Source**: Product matching pipeline
- **Format**: CSV files with similarity scores and classifications
- **Purpose**: Identify similar products across retailers

## Processing Flow

1. **Raw Data** → Basic cleaning → **Intermediate Cleaned**
2. **Intermediate Cleaned** → Normalization → **Database Tables**  
3. **Database Tables** → Matching → **Matching Results**
4. **Database Tables** → Import → **PostgreSQL Database**

## File Naming Convention

- Raw: `all_search_results_YYYYMMDD_HHMMSS.csv`
- Intermediate: `cleaned_products_YYYYMMDD_HHMMSS.csv`
- Normalized: `{table_name}_YYYYMMDD_HHMMSS.csv`
- Final: `{table_name}.csv` (in database_to_import/)
