# Auê Natural - Competitive Pricing Intelligence System

## 🎯 Project Overview
Advanced product matching engine for competitive pricing analysis in the natural beauty market. Uses hybrid lexical + semantic matching to identify identical products across retailers.

## 📊 Key Results
- **888 unique products** processed from 11,800+ scraped records
- **934 match pairs** identified (73.6% improvement over baseline)
- **56% coverage** - dramatic improvement from 35% baseline
- **Production ready** with automated pipeline

## 🚀 Quick Start

### Option 1: Full Automation with Dashboard Updates
```bash
# Setup PowerBI credentials (one-time)
python setup_powerbi.py

# Run complete pipeline with auto-dashboard updates
python run_complete_pipeline.py
```

### Option 2: Data Processing Only  
```bash
python3 run_pipeline.py
```

### Access Results

**Dashboards** (with auto-updates):
- Executive summary and competitive insights
- Real-time pricing intelligence 
- Market positioning analytics

**Data Files**:
```bash
data/processed/FINAL_MATCHES.csv    # 934 matched product pairs
data/processed/FINAL_UNMATCHED.csv  # 391 unmatched products  
data/processed/FINAL_SUMMARY.json   # Complete statistics
powerbi_data/                       # Dashboard-ready files (auto-updated)
```

## 🏗️ Architecture

```
├── src/                          # Core engines
│   ├── enhanced_matching_engine.py    # Main matching algorithm
│   ├── oxylabs_googleshopping_script.py  # Data collection
│   └── deduplication_manager.py        # Data deduplication
├── scripts/                      # Automation
│   ├── automated_matching_pipeline.py  # Complete pipeline
│   └── post_process_unmatched.py      # Additional recovery
├── data/
│   ├── raw/                      # Scraped data
│   └── processed/                # Final results
└── docs/                         # Analysis & reports
    └── Final_Results_Summary.md  # Comprehensive analysis
```

## 🔧 Technology Stack
- **Python 3.8+** with pandas, scikit-learn
- **Sentence-BERT** for semantic embeddings
- **PowerBI Integration** for automatic dashboard updates
- **REST API** for real-time dashboard refresh

## 📈 Automatic Dashboard Updates

When you run the pipeline, dashboards update automatically on the front-end:
- ✅ **No manual refresh needed**
- ✅ **Real-time competitive intelligence** 
- ✅ **Stakeholder-ready visualizations**

See [DASHBOARD_AUTOMATION.md](DASHBOARD_AUTOMATION.md) for setup details.  
- **RapidFuzz** for lexical similarity
- **Hybrid scoring** (60% lexical + 40% semantic)

## 📈 Business Impact
- **73.6% MORE** product pairs for price comparison
- **21.1 percentage points** better coverage
- **32.4% FEWER** products requiring manual intervention

## 🎖️ Match Quality
- **109 perfect matches** (100% similarity)
- **High confidence** matches above 85% similarity
- **Semantic understanding** captures meaning beyond exact words

---
*Production system for Auê Natural market entry strategy*
