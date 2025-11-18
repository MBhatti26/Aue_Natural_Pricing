# 🛍️ Aue Natural Price Monitoring Data Pipeline

**Automated data processing pipeline for collecting and analyzing beauty product pricing data from Google Shopping via Oxylabs.**

---

## 🚀 Quick Start

### For New Data Processing (Most Common)
```bash
# Run this command whenever new data has been scraped
python scripts/process_new_data.py
```

### For Product Matching & Price Comparison
```bash
# Run the enhanced matching engine with vector embeddings
python scripts/run_production_matching.py
```

### First Time Setup
```bash
# One-time setup
chmod +x setup.sh
./setup.sh
```

---

## 📋 What This Pipeline Does

1. **📥 Data Collection**: Scrapes Google Shopping data using Oxylabs API
2. **🔄 Data Processing**: Normalizes raw data into database-ready CSV files  
3. **✅ Data Validation**: Ensures data quality and relationships
4. **📊 Database Preparation**: Creates clean CSV files ready for import
5. **🤝 Product Matching**: Uses enhanced semantic matching with vector embeddings for price comparison
6. **📈 Business Intelligence**: Generates consolidated outputs for analytics and reporting

---

## 🗂️ File Organization

### Input Data
- `data/raw/all_search_results_YYYYMMDD_HHMMSS.csv` - Raw Oxylabs results
- Contains ~1,000+ product records across 4 categories

### Processed Data  
- `data/processed/` - **Latest timestamped outputs (one per run)**
  - `processed_matches_YYYYMMDD_HHMMSS.csv` - Main matching results
  - `unmatched_products_YYYYMMDD_HHMMSS.csv` - Unmatched products 
  - `processing_summary_YYYYMMDD_HHMMSS.json` - Processing metadata
  - `embeddings_cache.pkl` - Cached vector embeddings for performance
  - `archive_old_files/` - Historical files and intermediates
- `database_to_import/` - **Final CSV files ready for database import**

### Scripts
- `scripts/process_new_data.py` - **Main automation script**
- `scripts/run_production_matching.py` - **Enhanced product matching pipeline**
- `scripts/post_process_unmatched.py` - Additional match recovery
- `scripts/consolidate_outputs.py` - BI-ready output generation
- `scripts/validate_data.py` - Data quality validation
- `scripts/update_database_files.py` - Manual file update helper

---

## 📊 Database Schema

### Tables Created
```
📁 brand_name.csv        → Unique product brands (681 brands)
📁 category_name.csv     → Product categories (4 categories)  
📁 price_source.csv      → Data sources (Oxylabs Google Shopping)
📁 retailer_name.csv     → Online retailers (370+ retailers)
📁 product.csv           → Products with relationships (939 products)
📁 price_history.csv     → Price records with timestamps (1,033+ prices)
```

### Key Relationships
```
price_source ──→ retailer_name ──→ price_history
brand_name ──→ product ──→ price_history  
category_name ──→ product
```

---

## 🎯 For Next Time You Scrape New Data

### Simple Process (3 commands):
```bash
# 1. Activate environment  
source venv/bin/activate

# 2. Process new data (finds latest automatically)
python scripts/process_new_data.py

# 3. Validate everything is correct
python scripts/validate_data.py
```

### What These Commands Do:
1. **Finds** the latest raw data file automatically
2. **Processes** it through the cleaning pipeline  
3. **Updates** all CSV files in `database_to_import/`
4. **Validates** data quality and relationships
5. **Generates** a processing report

---

## 📈 Expected Data Volumes

| Category | Records | Description |
|----------|---------|-------------|
| **Shampoo Bar** | ~260 products | Solid shampoo products |
| **Conditioner Bar** | ~240 products | Solid conditioner products |  
| **Face Serum** | ~265 products | Facial skincare serums |
| **Body Butter** | ~265 products | Body moisturizing products |

**Total**: ~1,030 products from 370+ retailers across 680+ brands

---

## 🔍 Data Quality Checks

The validation automatically checks:
- ✅ **Primary Keys**: No duplicates in ID columns
- ✅ **Foreign Keys**: All relationships valid  
- ✅ **Data Quality**: No missing required fields
- ✅ **Business Logic**: Expected categories and price ranges
- ✅ **File Completeness**: All required CSV files present

---

## 🤝 Enhanced Product Matching Engine

### Key Performance Metrics
- **56% Coverage**: 837 total matching pairs across 888 products
- **35% Improvement**: Over original lexical-only matching approach
- **Semantic Understanding**: Vector embeddings with Sentence-BERT
- **Post-Processing Recovery**: Additional matches from unmatched products

### Matching Features
1. **Hybrid Scoring**: Combines lexical (60%) + semantic (40%) similarity
2. **Vector Embeddings**: `all-MiniLM-L6-v2` Sentence-BERT model
3. **Embedding Caching**: Persistent cache for improved performance
4. **Multi-Retailer Support**: Matches identical products across different retailers
5. **Quality Tiers**: Perfect matches (≥88%) and similar matches (≥65%)

### Business Impact
- **Better Price Comparison**: 35% more product pairs available
- **Reduced Unmatched Products**: 21.6% fewer products without matches  
- **Enhanced User Experience**: Semantic matching captures product relationships
- **BI-Ready Outputs**: Single consolidated CSV per matching run

### Output Files (Per Run)
- `processed_matches_YYYYMMDD_HHMMSS.csv` - All matching pairs with confidence scores
- `unmatched_products_YYYYMMDD_HHMMSS.csv` - Products still needing matches
- `processing_summary_YYYYMMDD_HHMMSS.json` - Performance metrics and metadata

---

## 🛠️ Technical Details

### Environment
- **Python 3.14+** with virtual environment
- **pandas, numpy** for data processing  
- **CSV format** for maximum compatibility

### File Naming
- Raw: `all_search_results_YYYYMMDD_HHMMSS.csv`
- Processed: `{table_name}_YYYYMMDD_HHMMSS.csv`  
- Final: `{table_name}.csv` (ready for import)

### Categories Tracked
1. **Shampoo Bar** - Solid hair cleansing products
2. **Conditioner Bar** - Solid hair conditioning products  
3. **Face Serum** - Concentrated facial treatments
4. **Body Butter** - Rich body moisturizers

---

## 📞 Support

### If Something Goes Wrong:
1. Check the processing report generated in project root
2. Run validation: `python scripts/validate_data.py`
3. Check virtual environment: `source venv/bin/activate`

### Manual Override:
```bash
# If automation fails, run steps manually:
source venv/bin/activate
python src/cleandata_script.py data/raw/[latest_file].csv data/processed  
python scripts/update_database_files.py
python scripts/validate_data.py
```

---

## 🎉 Success Indicators

### Data Processing Pipeline
When everything works correctly, you'll see:
- ✅ **Processing report** generated
- ✅ **All validation checks** passed  
- ✅ **6 CSV files** updated in `database_to_import/`
- ✅ **~1,000+ records** ready for database import

### Product Matching Pipeline
When matching runs successfully, you'll get:
- ✅ **56% product coverage** with 837+ matching pairs
- ✅ **3 timestamped files** in `data/processed/`
- ✅ **Performance summary** in JSON format
- ✅ **BI-ready output** for analytics and reporting

**The complete pipeline delivers both clean data and intelligent product matching! 🚀**

---
*Last Updated: November 18, 2025 | Pipeline Version: 2.0 (Enhanced Matching)*
