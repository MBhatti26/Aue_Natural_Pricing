# Auê Natural — Automated Dynamic Pricing Pipeline

## 1) Overview
This repository implements an end-to-end, automated pricing intelligence pipeline for **Auê Natural**.  
It collects competitive pricing from multiple retailers via **Google Shopping (Oxylabs)**, cleans and standardizes product data, performs **pairwise deduplication & matching** (with URL/thumbnail checks to avoid duplicates), and ingests results into a relational database for analysis and dynamic pricing.

**Key goals**
- Reliable daily ingestion of multi-retailer pricing
- High-precision product matching across noisy catalogs
- Traceable records (URLs, thumbnails) to audit duplicates and drift
- Warehouse-ready tables powering dashboards and pricing rules

---

## 2) Data Collection (Google Shopping via Oxylabs)
- **Source**: Google Shopping results fetched through **Oxylabs**.
- **Coverage**: Multiple retailers (UK focus first; extendable to EU/US/UAE).
- **Scheduling**: Daily pulls (cron/runner).  
- **Captured fields (typical)**: query, product title, price, currency, brand (when present), retailer, URL, image/thumbnail URL, collected timestamp, raw attributes.

**Anti-duplication inputs captured at source**
- **Canonical product URL**
- **Thumbnail URL (or image hash when available)**
- **Retailer domain + seller slug**

---

## 3) Data Cleaning & Normalization
Cleaning tackles the messiness of marketplace and aggregator data. The script applies multiple techniques, including:

- **String normalization**: Unicode normalization, whitespace collapse, punctuation trimming, case-folding.
- **Token discipline**: stopword removal for beauty domain (“for”, “with”, “and”), number/unit harmonization (ml, g, oz → canonical), hyphen/slash handling.
- **Brand extraction & standardization**: brand dictionaries + fallback heuristics (first token checks, “by <brand>” patterns).
- **Size parsing**: regex patterns for single and multi-pack (e.g., `2 x 100 ml`, `200ml`, `200 ml pack of 2`) → normalized `size_value`, `size_unit`, `pack_qty`.
- **Category cleaning**: map long tail categories to a compact set (e.g., Shampoo Bar, Body Butter, Face Serum), with a conservative “Unknown/Other”.
- **Price normalization**: currency capture as delivered; numeric coercion and outlier guards (e.g., £0, negative, extreme values).
- **URL & image guards**: canonicalization (strip utm/query noise when safe), optional image hash for future collision checks.

All cleaning steps are deterministic and reproducible so matched pairs are explainable.

---

## 4) Deduplication & Matching (Pairwise + Evidence Checks)
We use **pairwise logic** with blocking + similarity to find the best cross-retailer alignments:

**Blocking (reduce comparisons)**
- Same **brand** (after normalization)
- Overlapping **token sets** in product names (post-clean)
- Optional **category** equality

**Similarity features**
- Title similarity (token sort / partial token ratios)
- Brand exact/near-exact match
- Size/pack alignment (parsed numeric/unit consistency)
- Retailer signal (if comparing within-retailer duplicates)

**Evidence checks (to avoid false duplicates)**
- **URL guard**: same canonical URL → duplicate within day; skip inserting a second copy
- **Thumbnail guard**: identical thumbnail (or identical image hash) arriving the same day from the same retailer/query → treat as duplicate
- **New-entry rule**: new URL + new thumbnail (or new image hash) → admit as **new** record

**Match outcome classes**
- **Perfect**: high title similarity + brand agree + size agree
- **Best**: strong similarity with minor variance (e.g., pack count)
- **Similar**: plausible but needs human review
- **Unmatched**: held for enrichment / future passes

Daily summary includes counts for perfect/best/similar/unmatched and total insertions skipped due to URL/thumbnail duplication.

---

## 5) Database Ingestion (Warehouse-Ready)
Cleaned rows flow into a staging table and then into warehouse tables.

**Typical flow**
1. `stg_price_snapshot` ← daily cleaned pull  
2. Upserts into dimension/fact tables:
   - `aue.brand`
   - `aue.category`
   - `aue.product` (one row per canonical product with normalized fields)
   - `aue.retailer`
   - `aue.price_history` (facts: product–retailer–date–price–currency)
   - `aue.match_event` (optional audit: matched pair IDs, similarity, reasons)
   - `aue.ingestion_log` (run metadata, file batch, record counts)

**Notes**
- Keys: surrogate integer keys for dims; natural keys retained (URL, retailer_sku if any).
- Idempotency: load is safe to re-run; URL/thumbnail guards prevent duplicate daily inserts.
- Partitioning option: `price_history` by date to speed trend queries.

---

## 6) Automation & Monitoring
- **Scheduler**: cron or workflow runner (local or CI).
- **Health checks**: row count deltas vs. prior day, duplicate-skip counts, unmatched ratio threshold alerts.
- **Artifacts**: daily CSV/JSON snapshot (optional) + ingestion logs.

---

## 7) Outputs & Analytics
- **Matched product sets** across retailers for like-for-like price comparison.
- **Daily price deltas** and **trend series** per product/retailer.
- **Unmatched inventory** report for enrichment loops.
- **Category/brand competitiveness** and **promotion tracking**.

---

## 8) Repository Structure
```
Final_Project_Aue_Natural/
├── README.md
├── pyproject.toml
├── requirements.txt
├── setup.sh
├── run_all.sh               # end-to-end automation pipeline
├── logs/                    # pipeline run logs
├── src/                     # ETL, cleaning, matching
├── scripts/                 # orchestrators, QA, setup utilities
├── sql/                     # DDL/DML, schema, test queries
├── data/                    # raw and cleaned snapshots (ignored in git)
├── database_to_import/      # load-ready CSVs
└── docs/
    ├── DATABASE_SETUP_GUIDE.md
    ├── Proposal Aue Natural_21154568.docx
    └── Papers cited/
```

---

## 9) Setup & Run

### 9.1 One-Command Setup
```bash
chmod +x setup.sh
./setup.sh
```
This installs dependencies, sets up the `.env` file, initializes the PostgreSQL schema, and runs the first pipeline execution.

### 9.2 Full End-to-End Automation
```bash
chmod +x run_all.sh
./run_all.sh
```
This executes the complete ETL flow:

| Step | Script | Description |
|------|---------|-------------|
| 1 | `src/oxylabs_googleshopping_script.py` | Extract data from Google Shopping via Oxylabs |
| 2 | `src/cleandata_script.py` | Clean and normalize products |
| 3 | `src/deduplication_manager.py` | Pairwise fuzzy matching + URL/thumbnail guards |
| 4 | `src/import_all_CSVs.py` | Load cleaned and matched data into PostgreSQL |
| 5 | `scripts/validate_data.py` | Optional QA validation |

Logs are saved under `logs/run_pipeline_<timestamp>.log`.

### 9.3 Manual Setup (optional)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
psql -h localhost -U aue -d aue_warehouse -f sql/create_schema.sql
python scripts/run_pipeline.py
```

---

## 10) Data Quality & Governance
- **Deterministic cleaning** and versioned rules.
- **Provenance**: store raw dump path + oxylabs job/rid in `ingestion_log`.
- **Auditability**: retain URL and thumbnail references for traceability.
- **Monitoring**: unmatched% and duplicate-skip% thresholds trigger alerts.

### 10.1 Environment Variables
All credentials and configuration values are stored in `.env` (ignored by Git).  
Template: `env.example`

```
OXYLABS_USERNAME=your_username
OXYLABS_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aue_warehouse
DB_USER=aue
DB_PASSWORD=your_password
REGION=uk
RUN_MODE=prod
```

---

## 11) Pricing Engine Integration (Next Step)
The warehouse powers dynamic pricing logic:
- Competitive position bands (below / at / above market median)
- Price floors and ceilings by brand or category
- Promotion detection (rapid price delta analysis)
- Candidate adjustments emitted as pricing recommendations

---

## 12) Maintainers
- **Mahnoor Bilal** — MSc Data Science, University of Westminster  
  Project: Auê Natural Global Pricing Intelligence

---

### Why a Single README
A single README ensures all setup and execution instructions remain self-contained.  
Future documentation can expand into:
- `docs/SCHEMA.md` — database ERD and table dictionary  
- `docs/ALGO_MATCHING.md` — fuzzy-matching thresholds and error handling
