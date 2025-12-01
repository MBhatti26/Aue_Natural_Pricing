# Auê Natural - Product Price Monitoring & Matching Pipeline

**Advanced Product Matching Engine with Semantic Similarity for Competitive Price Intelligence**

---

## 📋 Project Overview

This project implements an intelligent product matching and price monitoring system for Auê Natural's beauty and personal care products. The pipeline scrapes Google Shopping data, matches products across retailers using advanced semantic similarity algorithms, and generates actionable pricing intelligence for competitive analysis.

### Key Features

- 🔍 **Google Shopping Scraper** - Automated data collection via Oxylabs API
- 🧠 **Hybrid Matching Engine** - Combines lexical (RapidFuzz + Jaccard) and semantic similarity (Sentence-BERT)
- 🏷️ **Retailer Standardization** - Normalizes merchant names across data sources
- 📦 **Multipack/Variant Parsing** - Intelligent size normalization (e.g., "3 x 50ml" → 150ml)
- 🔄 **Deduplication** - Advanced deduplication with temporal price snapshots
- 📊 **Power BI Integration** - Automated dashboard data preparation
- 🗄️ **PostgreSQL Database** - Structured data warehouse with schema management

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Google Shopping API                        │
│                      (Oxylabs)                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Data Collection & Storage                      │
│            (src/oxylabs_googleshopping_script.py)           │
│                  → data/raw/*.csv                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             Data Cleaning & Normalization                    │
│              (src/cleandata_script.py)                       │
│   • Retailer standardization                                 │
│   • Multipack parsing                                        │
│   • Size normalization                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL Data Warehouse                      │
│                  (database_to_import/)                       │
│   Tables: product, brand, category, retailer,               │
│           stg_price_snapshot                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Enhanced Matching Engine (Hybrid AI)                │
│         (src/enhanced_matching_engine.py)                    │
│   • Lexical: RapidFuzz + Jaccard similarity                 │
│   • Semantic: Sentence-BERT embeddings                      │
│   • Brand-weighted scoring                                   │
│   • Size-aware matching                                      │
│   • Category filtering                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Outputs & Analytics                         │
│                                                              │
│  • data/processed/processed_matches.csv                     │
│  • data/processed/unmatched_products.csv                    │
│  • powerbi_data/FINAL_MATCHES.csv                           │
│  • powerbi_data/FINAL_UNMATCHED.csv                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Oxylabs API credentials
- Virtual environment (recommended)

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd Final_Project_Aue_Natural

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp env.example .env
# Edit .env with your credentials:
#   - OXYLABS_USERNAME
#   - OXYLABS_PASSWORD
#   - PostgreSQL connection details

# 5. Initialize database
psql -U postgres -f sql/create_schema.sql
```

### Running the Pipeline

**Option 1: Complete Pipeline (Recommended)**
```bash
python run_complete_pipeline.py
```

**Option 2: Step-by-Step**
```bash
# Step 1: Scrape Google Shopping data
python src/oxylabs_googleshopping_script.py

# Step 2: Clean and import to database
python src/cleandata_script.py

# Step 3: Run matching engine
python src/enhanced_matching_engine.py

# Step 4: Prepare Power BI data
python scripts/prepare_powerbi_data.py
```

**Option 3: Shell Script**
```bash
./run_all.sh
```

---

## 📂 Repository Structure

```
Final_Project_Aue_Natural/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── run_complete_pipeline.py          # Main pipeline orchestrator
├── run_all.sh                        # Shell convenience script
├── .gitignore                        # Git ignore rules
├── .env                              # Environment variables (not in git)
├── env.example                       # Template for .env
│
├── src/                              # Core processing engines
│   ├── oxylabs_googleshopping_script.py  # Data scraper
│   ├── enhanced_matching_engine.py   # Hybrid AI matcher
│   ├── matching_engine.py            # Legacy matcher
│   ├── deduplication_manager.py      # Dedup logic
│   ├── cleandata_script.py           # Data cleaning
│   ├── file_based_enhanced_matcher.py
│   └── archive/                      # Old versions
│
├── scripts/                          # Utilities & automation
│   ├── automated_matching_pipeline.py
│   ├── prepare_powerbi_data.py       # Power BI data prep
│   ├── run_pipeline.py
│   ├── post_process_unmatched.py
│   ├── powerbi_auto_update.py
│   ├── cleanup_processed.py
│   ├── consolidate_outputs.py
│   ├── process_new_data.py
│   ├── update_database_files.py
│   ├── brand_analysis.py
│   ├── debug_matching.py
│   ├── setup_powerbi.py
│   ├── auto_generate_powerbi_dashboards.py
│   ├── create_powerbi_quickstart.py
│   └── archive/
│
├── data/
│   ├── raw/                          # Raw Google Shopping CSVs
│   │   └── archive/
│   ├── processed/                    # Processed outputs
│   │   ├── processed_matches.csv
│   │   ├── unmatched_products.csv
│   │   └── embeddings_cache.pkl      # ML model cache
│   └── logs/
│
├── powerbi_data/                     # Power BI data exports
│   ├── FINAL_MATCHES.csv
│   └── FINAL_UNMATCHED.csv
│
├── database_to_import/               # Database staging area
│   ├── product.csv
│   ├── brand_*.csv
│   ├── category_*.csv
│   └── archive/
│
├── sql/                              # Database schema & queries
│   ├── create_schema.sql
│   ├── mysql_schema.sql
│   ├── mysql_import_data.sql
│   └── archive/
│
├── docs/                             # Documentation
│   ├── Cleanup_Summary.md
│   ├── Enhanced_Matching_Results.md
│   ├── Complete_Pipeline_Run_20251119.md
│   ├── Write Up Aue Natural_21154568.docx
│   ├── Papers cited/
│   └── archive/
│
└── logs/                             # Application logs
    └── run_pipeline_*.log
```

---

## 🧪 Matching Algorithm

The enhanced matching engine uses a **hybrid scoring approach**:

### Components

1. **Lexical Similarity (60% weight)**
   - RapidFuzz token_set_ratio (fuzzy string matching)
   - Jaccard token overlap (set-based similarity)

2. **Semantic Similarity (40% weight)**
   - Sentence-BERT embeddings (all-MiniLM-L6-v2 model)
   - Cosine similarity on vector representations
   - Cached embeddings for performance

3. **Additional Scoring Factors**
   - Brand matching: +20 (same) / -25 (different)
   - Size similarity: +20 (exact) / +10 (within 20%) / -10 (different units)
   - Subcategory keywords: +10 (match) / -15 (mismatch)
   - Category filtering: Only compare products within same category

### Thresholds

- **Minimum similarity**: 65/100
- **Size tolerance**: ±20%
- **Perfect match**: 88+/100

### Data Quality Enhancements

✅ **Retailer Standardization**: "boots uk", "boots.com" → "boots"  
✅ **Multipack Parsing**: "3 x 50ml" → 150ml  
✅ **Incomplete Record Filtering**: Drops products missing price, size, or title  
✅ **Deduplication**: Removes exact duplicates while preserving price history  

---

## 📊 Outputs

### 1. Matched Products
**Location**: `data/processed/processed_matches.csv`, `powerbi_data/FINAL_MATCHES.csv`

Columns:
- Product IDs, names, brands, categories
- Prices, sizes, retailers for both products
- Similarity scores (overall, lexical, semantic, brand, size)

### 2. Unmatched Products
**Location**: `data/processed/unmatched_products.csv`, `powerbi_data/FINAL_UNMATCHED.csv`

Products with no matches above threshold - kept for catalog completeness but don't affect price optimization.

### 3. Embeddings Cache
**Location**: `data/processed/embeddings_cache.pkl`

Cached sentence embeddings to speed up subsequent runs (automatically managed).

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Oxylabs API Credentials
OXYLABS_USERNAME=your_username
OXYLABS_PASSWORD=your_password

# PostgreSQL Database
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aue_warehouse
```

### Matching Thresholds (src/enhanced_matching_engine.py)

```python
MIN_SIMILARITY = 65          # Minimum score for match
PERFECT_THRESHOLD = 88       # Perfect match threshold
SIZE_TOLERANCE = 0.20        # 20% size difference allowed
LEXICAL_WEIGHT = 0.6         # Weight for lexical similarity
SEMANTIC_WEIGHT = 0.4        # Weight for semantic similarity
```

---

## 🔧 Troubleshooting

### Issue: Empty embeddings cache or slow first run
**Solution**: First run will download Sentence-BERT model (~80MB). Subsequent runs use cached embeddings.

### Issue: PostgreSQL connection errors
**Solution**: Verify credentials in `.env` and ensure PostgreSQL is running:
```bash
# Check if PostgreSQL is running
pg_isready

# Restart PostgreSQL (macOS)
brew services restart postgresql@14
```

### Issue: Oxylabs API errors
**Solution**: 
- Check credits in your Oxylabs dashboard
- Verify credentials in `.env`
- Reduce pagination in `src/oxylabs_googleshopping_script.py` if hitting rate limits

### Issue: No matches found
**Solution**:
- Lower `MIN_SIMILARITY` threshold (currently 65)
- Check if categories are properly assigned
- Review `data/processed/unmatched_products.csv` for insights

---

## 📈 Results Summary

**Latest Run (November 28, 2025)**:
- **Input rows**: 960 (raw Google Shopping + catalog data)
- **Unique product-retailer rows**: 159 (after cleaning & deduplication)
- **Matching pairs found**: 77
- **Unmatched SKUs**: 82
- **Data quality**: Significantly improved with enhancements

**Key Improvements**:
- Multipack/variant parsing added
- Retailer name standardization implemented
- Incomplete records filtered out
- Semantic similarity layer added
- Brand and size scoring enhanced

---

## 📚 Documentation

Detailed documentation available in `/docs/`:
- `Enhanced_Matching_Results.md` - Algorithm details and results
- `Complete_Pipeline_Run_20251119.md` - Full pipeline execution log
- `Cleanup_Summary.md` - Data cleaning process
- `Write Up Aue Natural_21154568.docx` - Academic write-up

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature/your-feature`
5. Create Pull Request

---

## 📄 License

This project is part of an academic research project for Auê Natural.

---

## 🙏 Acknowledgments

- **Oxylabs** - Google Shopping API provider
- **Sentence-Transformers** - Semantic similarity models
- **RapidFuzz** - Fast fuzzy string matching
- **PostgreSQL** - Data warehouse

---

**Last Updated**: December 1, 2025  
**Version**: 2.0 (Enhanced with Semantic Matching)
