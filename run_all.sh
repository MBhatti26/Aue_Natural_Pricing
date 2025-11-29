#!/bin/bash

echo "=============================================================="
echo "       Starting Auê Natural Full Pipeline Run"
echo "=============================================================="

# 1 — Activate venv
if [ -d "venv" ]; then
    echo "[1/6] Activating virtual environment..."
    source venv/bin/activate
else
    echo "[1/6] No venv found. Continuing with system Python."
fi

# 2 — Identify newest raw file
LATEST_RAW=$(ls -t data/raw/*.csv | head -n 1)
echo "Latest raw file detected: $LATEST_RAW"

echo "[2/6] Cleaning latest raw extraction..."
python3 src/cleandata_script.py "$LATEST_RAW"

# 3 — Identify newest cleaned file
LATEST_CLEANED=$(ls -t cleaned_products_*.csv | head -n 1)
echo "Latest cleaned file detected: $LATEST_CLEANED"

echo "[3/6] Deduplicating cleaned data..."
python3 src/deduplication_manager.py "$LATEST_CLEANED"

# 4 — Load into database
echo "[4/6] Loading into database..."
python3 src/load_to_db.py

# 5 — Run enhanced product matching
echo "[5/6] Running enhanced product matching..."
python3 scripts/run_production_matching.py

# 6 — Run database validation
echo "[6/6] Running validation..."
python3 scripts/validate_data.py



echo "=============================================================="
echo "         Auê Natural Pipeline Completed Successfully!"
echo "=============================================================="
