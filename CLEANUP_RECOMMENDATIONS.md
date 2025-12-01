# Repository Cleanup Recommendations

Generated: December 1, 2025

## Priority 1: Critical Issues

### 1. Update .gitignore
Add these entries:
```
# Backup files
*.bak

# Large data files
data/raw/*.csv
data/processed/*.csv
data/processed/*.pkl
data/processed/seen_*.json

# Virtual environments
.venv/
venv/

# PowerBI data (regenerated)
powerbi_data/*.csv
```

### 2. Fix Empty README.md
Your main README.md is empty! Should contain:
- Project overview
- Setup instructions
- Pipeline workflow
- Usage examples
- References to other docs

### 3. Remove Backup Files
```bash
find . -name "*.bak" -delete
```

## Priority 2: Organization Improvements

### 4. Move Root-Level Scripts to /scripts/
Move these files:
- `auto_generate_powerbi_dashboards.py` → `scripts/`
- `brand_analysis.py` → `scripts/`
- `create_powerbi_quickstart.py` → `scripts/`
- `debug_matching.py` → `scripts/`
- `setup_powerbi.py` → `scripts/`

Keep at root:
- `run_complete_pipeline.py` (main entry point)
- `run_all.sh` (convenience runner)
- `requirements.txt`
- `README.md`

### 5. Remove Empty Placeholder Files
Delete or implement:
- `scripts/demo_url_thumbnail.py` (0 bytes)
- `scripts/validate_data.py` (0 bytes)
- `src/import_all_CSVs.py` (0 bytes)
- `PowerBI_README.md` (0 bytes)
- `PowerBI_SIMPLE_SETUP.md` (0 bytes)

### 6. Consolidate Duplicate Data
Remove duplicates:
- Keep `powerbi_data/` for Power BI outputs
- Keep `data/processed/` for internal pipeline use
- Remove symlinks or pick one source of truth

## Priority 3: Documentation

### 7. Create Comprehensive README.md
Sections needed:
- Project Title & Description
- Features
- Installation
- Quick Start
- Pipeline Architecture
- Data Flow
- Configuration
- Usage Examples
- Troubleshooting
- Contributing
- License

### 8. Consolidate Documentation
- Move all `.md.bak` content to `/docs/archive/`
- Create a `/docs/README.md` with index
- Keep only active docs in `/docs/`

## Suggested Final Structure

```
Final_Project_Aue_Natural/
├── README.md                          # Main documentation
├── requirements.txt                   # Python dependencies
├── run_complete_pipeline.py          # Main pipeline runner
├── run_all.sh                        # Shell convenience script
├── .gitignore                        # Updated with recommendations
├── .env                              # Config (not in git)
├── env.example                       # Template
│
├── src/                              # Core engines
│   ├── enhanced_matching_engine.py   # Main matching logic
│   ├── matching_engine.py            # Legacy matcher
│   ├── deduplication_manager.py      # Dedup logic
│   ├── cleandata_script.py           # Data cleaning
│   ├── file_based_enhanced_matcher.py
│   └── archive/                      # Old versions
│
├── scripts/                          # Utilities & runners
│   ├── automated_matching_pipeline.py
│   ├── prepare_powerbi_data.py
│   ├── run_pipeline.py
│   ├── post_process_unmatched.py
│   ├── powerbi_auto_update.py
│   ├── cleanup_processed.py
│   ├── consolidate_outputs.py
│   ├── process_new_data.py
│   ├── update_database_files.py
│   ├── brand_analysis.py             # MOVED FROM ROOT
│   ├── debug_matching.py             # MOVED FROM ROOT
│   ├── setup_powerbi.py              # MOVED FROM ROOT
│   ├── auto_generate_powerbi_dashboards.py  # MOVED
│   ├── create_powerbi_quickstart.py  # MOVED
│   └── archive/                      # Old scripts
│
├── data/
│   ├── raw/                          # Raw Google Shopping CSVs
│   │   └── archive/                  # Old raw data
│   ├── processed/                    # Processed outputs
│   │   ├── processed_matches.csv     # Latest matches
│   │   ├── unmatched_products.csv    # Latest unmatched
│   │   └── embeddings_cache.pkl      # ML cache
│   └── logs/                         # Processing logs
│
├── powerbi_data/                     # Power BI specific
│   ├── FINAL_MATCHES.csv
│   └── FINAL_UNMATCHED.csv
│
├── database_to_import/               # DB staging
│   ├── product.csv
│   ├── brand_*.csv
│   ├── category_*.csv
│   └── archive/
│
├── sql/                              # Database scripts
│   ├── create_schema.sql
│   ├── mysql_schema.sql
│   ├── mysql_import_data.sql
│   └── archive/
│
├── docs/                             # Documentation
│   ├── README.md                     # Docs index
│   ├── Cleanup_Summary.md
│   ├── Enhanced_Matching_Results.md
│   ├── Complete_Pipeline_Run_20251119.md
│   ├── Write Up Aue Natural_21154568.docx
│   ├── Papers cited/
│   └── archive/                      # Old versions
│
└── logs/                             # Application logs
    └── run_pipeline_*.log
```

## Quick Cleanup Commands

```bash
# 1. Remove backup files
find . -name "*.bak" -delete

# 2. Move scripts to proper location
mv auto_generate_powerbi_dashboards.py scripts/
mv brand_analysis.py scripts/
mv create_powerbi_quickstart.py scripts/
mv debug_matching.py scripts/
mv setup_powerbi.py scripts/

# 3. Remove empty files
rm scripts/demo_url_thumbnail.py
rm scripts/validate_data.py
rm src/import_all_CSVs.py
rm PowerBI_README.md
rm PowerBI_SIMPLE_SETUP.md

# 4. Update .gitignore (see Priority 1)
# 5. Write README.md content
# 6. Commit changes
git add -A
git commit -m "Clean up repository structure and organization"
git push
```
