#!/usr/bin/env bash
# =====================================================
# Auê Natural Dynamic Pricing & Data Warehouse Setup
# =====================================================

set -e  # Exit immediately if a command fails

echo "====================================================="
echo "   Starting Auê Natural Project Setup"
echo "====================================================="

# --- 1. Check Poetry ---
if ! command -v poetry &> /dev/null
then
    echo "[1/5] Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "[1/5] Poetry already installed."
fi

# --- 2. Install dependencies ---
echo "[2/5] Installing dependencies..."
poetry install

# --- 3. Environment setup ---
if [ ! -f ".env" ]; then
    echo "[3/5] .env file not found. Creating from example..."
    cp env.example .env
    echo "⚠️  Please update .env with your credentials (DB, Oxylabs, etc.)"
else
    echo "[3/5] Using existing .env file."
fi

# --- 4. Initialize PostgreSQL schema ---
if [ -f "sql/create_schema.sql" ]; then
    echo "[4/5] Creating database schema..."
    export $(grep -v '^#' .env | xargs)
    psql -h ${DB_HOST:-localhost} -U ${DB_USER:-aue} -d ${DB_NAME:-aue_warehouse} -f sql/create_schema.sql
else
    echo "⚠️  Schema file not found. Skipping database setup."
fi

# --- 5. Run pipeline ---
echo "[5/5] Running data pipeline..."
poetry run python scripts/run_pipeline.py

echo "-----------------------------------------------------"
echo "✅ Setup complete! Project is ready to use."
echo "-----------------------------------------------------"